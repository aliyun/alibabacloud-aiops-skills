/**
 * 解析仪表板 JSON 数据
 *
 * 使用方式：
 *   - 作为 Python 脚本调用：node get_dashboard_json.js < dashboard.json
 *   - 或在 Node.js 中导入使用
 *
 * 输入：通过 OpenAPI 获取的仪表板原始 JSON 数据
 * 输出：解析后的仪表板结构化数据，包含：
 *   - basicInfo: 基本信息（名称、ID、URL）
 *   - queryControls: 查询控件列表
 *   - chartComponents: 图表组件列表
 *   - tabComponents: Tab 组件列表
 *   - richTextComponents: 富文本组件列表
 *   - layoutAnalysis: 布局分析结果
 *   - datasetSchemaMap: 数据集schema信息（用于字段别名解析）
 */

// 布局分析辅助函数 - 基于 tileLayout 的 x/y 坐标
function analyzeLayout(charts) {
  if (charts.length === 0) return { rows: [], source: 'none' };
  
  // 基于 tileLayout 的 y 坐标分组（同一行的 y 值相同或相近）
  const rowMap = {};
  
  charts.forEach(chart => {
    const y = chart.position.y || 0;
    // 找到最近的行（允许 y 值有小幅偏差）
    let targetY = y;
    for (const existingY of Object.keys(rowMap)) {
      if (Math.abs(parseInt(existingY) - y) < 5) {
        targetY = parseInt(existingY);
        break;
      }
    }
    
    if (!rowMap[targetY]) {
      rowMap[targetY] = { y: targetY, items: [] };
    }
    
    rowMap[targetY].items.push({
      chart: chart,
      x: chart.position.x || 0,
      w: chart.position.w || 1,
      h: chart.position.h || 1
    });
  });
  
  // 按行号（y 坐标）排序
  const sortedRows = Object.values(rowMap).sort((a, b) => a.y - b.y);
  
  // 每行内按 x 坐标排序
  sortedRows.forEach(row => {
    row.items.sort((a, b) => a.x - b.x);
    row.charts = row.items.map(item => item.chart);
    row.gridInfo = row.items.map(item => ({
      internalId: item.chart.internalId,
      x: item.x,
      y: row.y,
      w: item.w,
      h: item.h
    }));
    delete row.items;
  });
  
  return { rows: sortedRows, source: 'tileLayout' };
}

/**
 * 检查字符串是否为乱码（10位长度的十六进制字符串）
 * @param {string} str - 要检查的字符串
 * @returns {boolean} 是否为乱码
 */
function isGarbageString(str) {
  if (!str || typeof str !== 'string') return true;
  // 检查是否为10位长度的十六进制字符串（如 "bcdcf35a53"）
  return /^[a-f0-9]{10}$/i.test(str);
}

/**
 * 从数据集schema中查找字段的caption
 * @param {string} pathId - 字段的pathId
 * @param {Array} fields - 数据集schema中的fields数组
 * @returns {string|null} 字段caption，未找到返回null
 */
function findFieldCaptionFromSchema(pathId, fields) {
  if (!pathId || !fields || !Array.isArray(fields)) return null;

  for (const field of fields) {
    // 检查当前字段
    if (field.uniqueId === pathId || field.name === pathId) {
      return field.caption || null;
    }
    // 检查attributes中的子字段
    if (field.attributes && Array.isArray(field.attributes)) {
      for (const attr of field.attributes) {
        if (attr.uniqueId === pathId || attr.id === pathId) {
          return attr.caption || null;
        }
      }
    }
  }
  return null;
}

/**
 * 解析仪表板 JSON
 * @param {Object} json - 通过 OpenAPI 获取的仪表板原始 JSON 数据
 * @param {Object} datasetSchemaMap - 可选，数据集schema信息，用于字段别名解析
 * @returns {Object} 解析后的结构化数据
 */
function parseDashboardJson(json, datasetSchemaMap = {}) {
  try {
    // 1. 基本信息
    const basicInfo = {
      name: json.name,                    // 仪表板名称
      pageId: json.treeId,                // 页面ID
      workspaceId: json.workspaceId,      // 工作空间ID
      gmtModified: json.gmtModified,
    };

    // 2. 组件容器
    const queryControls = [];   // 查询控件
    const chartComponents = []; // 图表组件
    const tabComponents = [];   // Tab组件
    const richTextComponents = []; // 富文本组件

    // 内部ID到组件的映射
    const componentMap = {};

    // 确保 components 存在
    const components = json.components || [];

    components.forEach(comp => {
      const content = JSON.parse(comp.componentContent || '{}');
      const queryInput = JSON.parse(comp.queryInput || '{}');
      const internalId = content.id;

      // 从 tileLayout 提取位置信息（w/h/x/y）
      const tileLayout = content.tileLayout || {};
      const position = {
        x: tileLayout.x || 0,       // 栅格 x 坐标
        y: tileLayout.y || 0,       // 栅格 y 坐标
        w: tileLayout.w || 1,       // 栅格宽度
        h: tileLayout.h || 1,       // 栅格高度
        minW: tileLayout.minW || 1, // 最小宽度
        minH: tileLayout.minH || 1  // 最小高度
      };

      componentMap[internalId] = {
        componentId: comp.componentId,
        componentName: comp.componentName,
        customComponentId: comp.customComponentId,
        internalId: internalId,
        position: position
      };

      if (comp.customComponentId === 'query2') {
        // === 查询控件 ===
        const modelConfig = content.modelConfig || {};
        const fieldConfigs = modelConfig.fieldConfigs || [];
        const styleConfig = content.styleConfig || {};
        const needManualQuery = Array.isArray(styleConfig.buttons) && styleConfig.buttons.includes('query');
        const isSingleComponent = content.queryType === 'qbi-inside-chart' && content.parentId;
        const parentId = content.parentId || null;

        queryControls.push({
          componentId: comp.componentId,
          internalId: internalId,
          needManualQuery: needManualQuery,
          isSingleComponent: isSingleComponent,
          parentId: parentId,
          position: position,
          fields: fieldConfigs.map(f => ({
            id: f.id,
            labelName: f.labelName,
            componentType: f.componentType,   // datetime / enumSelect
            enumType: f.config?.enumType || 'single',
            isRequired: f.isRequired || false,
            defaultValue: f.defaultValue || null,
            // 时间控件的粒度
            timeGranularity: f.config?.timeGranularity || null,
            relatedGraphIds: (f.graphMappings || []).map(g => g.graphId)
          }))
        });

      } else if (comp.customComponentId === 'tab') {
        // === Tab 组件 ===
        const attr = content.attribute || {};
        const tabs = attr.tabs || content.items || [];

        tabComponents.push({
          componentId: comp.componentId,
          internalId: internalId,
          componentName: content.caption || 'Tab',
          activeId: content.activeId,
          position: position,
          tabs: tabs.map(tab => ({
            id: tab.id,
            title: tab.title || tab.text
          }))
        });

      } else if (comp.customComponentId === 'text') {
        // === 文本组件 ===
        const attr = content.attribute || {};
        // 提取纯文本内容（去除HTML标签）
        const htmlContent = attr.content || '';
        const textContent = htmlContent.replace(/<[^>]*>/g, '').trim();

        if (textContent) {
          richTextComponents.push({
            componentId: comp.componentId,
            internalId: internalId,
            position: position,
            htmlContent: htmlContent,
            textContent: textContent
          });
        }

      } else {
        // === 图表组件（非 query2、非 tab、非富文本）===
        const attr = content.attribute || {};
        const caption = attr.caption || comp.componentName || '';
        const parentId = content.parentId || null;

        // 获取当前图表的数据集ID
        const sourceId = queryInput.sourceId;
        const datasetSchema = sourceId ? datasetSchemaMap[sourceId] : null;
        const schemaFields = datasetSchema ? datasetSchema.fields : null;

        // 获取字段别名映射（funcSettingMap）
        const funcSettingMap = attr.funcSettingMap || {};

        // 辅助函数：获取字段别名
        // 优先级：1. funcSettingMap.aliasName（非乱码） 2. cubeSchema.fields.caption 3. col.caption 4. col.name
        const getFieldCaption = (col) => {
          const uuid = col.uuid;
          const pathId = col.pathId;

          // 1. 尝试从 funcSettingMap 获取别名
          if (uuid && funcSettingMap[uuid] && funcSettingMap[uuid].aliasName) {
            const aliasName = funcSettingMap[uuid].aliasName;
            // 检查别名是否为乱码（10位十六进制字符串）
            if (!isGarbageString(aliasName)) {
              return aliasName;
            }
          }

          // 2. 尝试从 cubeSchema.fields 中匹配 pathId 获取 caption
          if (pathId && schemaFields) {
            const schemaCaption = findFieldCaptionFromSchema(pathId, schemaFields);
            if (schemaCaption) {
              return schemaCaption;
            }
          }

          // 3. 降级到 col.caption 或 col.name
          return col.caption || col.name;
        };
        
        // 解析 queryInput.area 获取字段配置
        const areas = queryInput.area || [];
        const dimensions = [];  // 维度字段
        const measures = [];    // 度量字段
        const filters = [];     // 过滤器字段
        const drillFields = []; // 下钻字段
        
        areas.forEach(area => {
          // 提取下钻字段（id 为 drill 的 area）
          if (area.id === 'drill') {
            (area.columnList || []).forEach(col => {
              drillFields.push({
                caption: getFieldCaption(col),
                pathId: col.pathId,
                itemType: col.itemType,
                key: col.key,
                uuid: col.uuid,
                isDrillEnabled: col.isDrillEnabled || false
              });
            });
            return; // drill area 处理完毕，跳过后续逻辑
          }
          
          // 处理其他 area（维度、度量、过滤器）
          (area.columnList || []).forEach(col => {
            const fieldInfo = {
              caption: getFieldCaption(col),
              pathId: col.pathId,
              itemType: col.itemType,  // dimension / measure / datetime / geographic
              key: col.key,
              uuid: col.uuid,
              aggregateType: col.aggregator || col.aggregateType || null,
              isDrillEnabled: col.isDrillEnabled || false
            };
            
            if (area.id === 'filters' || area.queryAxis === 'filters') {
              filters.push(fieldInfo);
            } else if (col.itemType === 'measure') {
              measures.push(fieldInfo);
            } else {
              dimensions.push(fieldInfo);
            }
          });
        });
        
        // 提取默认过滤器配置
        const filterConfigs = content.filterConfigs || queryInput.filter || [];
        
        chartComponents.push({
          componentId: comp.componentId,
          internalId: internalId,
          componentName: caption,
          componentType: comp.componentType,
          customComponentId: comp.customComponentId,
          sourceId: queryInput.sourceId,          // 数据集ID - 问数调用的关键
          position: position,                      // 位置信息（来自 tileLayout）
          dimensions: dimensions,                  // 维度字段
          measures: measures,                      // 度量字段
          filters: filters,                        // 过滤器字段
          drillFields: drillFields,               // 下钻字段
          defaultFilters: filterConfigs,          // 默认过滤器
          parentId: parentId
        });
      }
    });
    
    // 3. 建立图表与 Tab 的从属关系
    chartComponents.forEach(chart => {
      chart.tabInfo = null;
      
      if (chart.parentId) {
        for (const tab of tabComponents) {
          for (const tabItem of tab.tabs) {
            const expectedParentId = tab.internalId + tabItem.id;
            if (chart.parentId === expectedParentId) {
              chart.tabInfo = {
                tabComponentId: tab.componentId,
                tabInternalId: tab.internalId,
                tabItemId: tabItem.id,
                tabItemTitle: tabItem.title
              };
              break;
            }
          }
          if (chart.tabInfo) break;
        }
      }
    });
    
    // 4. 建立查询控件与图表的关联关系
    chartComponents.forEach(chart => {
      chart.relatedQueryControls = [];
      
      queryControls.forEach(qc => {
        if (qc.isSingleComponent && qc.parentId === chart.internalId) {
          chart.relatedQueryControls.push({
            componentId: qc.componentId,
            type: 'single-component',
            fields: qc.fields.map(f => f.labelName)
          });
        } else if (!qc.isSingleComponent) {
          const matchedFields = qc.fields.filter(f => 
            f.relatedGraphIds.includes(chart.internalId)
          );
          if (matchedFields.length > 0) {
            chart.relatedQueryControls.push({
              componentId: qc.componentId,
              type: 'global',
              fields: matchedFields.map(f => f.labelName)
            });
          }
        }
      });
    });
    
    // 5. 为查询控件字段添加关联图表名称
    queryControls.forEach(qc => {
      qc.fields.forEach(f => {
        f.relatedCharts = f.relatedGraphIds.map(gid => {
          const chart = chartComponents.find(c => c.internalId === gid);
          return chart ? { internalId: gid, name: chart.componentName } : { internalId: gid, name: '未知图表' };
        });
      });
    });
    
    // 6. 布局分析 - 基于 tileLayout 的 x/y 坐标
    const layoutAnalysis = analyzeLayout(chartComponents);

    return {
      success: true,
      basicInfo,
      queryControls,
      chartComponents,
      tabComponents,
      richTextComponents,
      layoutAnalysis,
      datasetSchemaMap  // 保留数据集schema信息，供后续使用
    };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

// 如果作为命令行脚本运行
if (typeof require !== 'undefined' && require.main === module) {
  let inputData = '';

  process.stdin.setEncoding('utf8');
  process.stdin.on('readable', () => {
    let chunk;
    while ((chunk = process.stdin.read()) !== null) {
      inputData += chunk;
    }
  });

  process.stdin.on('end', () => {
    try {
      const parsedInput = JSON.parse(inputData);

      // 支持两种输入格式：
      // 1. 新格式：{ dashboardJson: {...}, datasetSchemaMap: {...} }
      // 2. 旧格式：直接的仪表板 JSON {...}
      let dashboardJson;
      let datasetSchemaMap = {};

      if (parsedInput.dashboardJson && parsedInput.datasetSchemaMap !== undefined) {
        // 新格式
        dashboardJson = parsedInput.dashboardJson;
        datasetSchemaMap = parsedInput.datasetSchemaMap || {};
      } else {
        // 旧格式（向后兼容）
        dashboardJson = parsedInput;
      }

      const result = parseDashboardJson(dashboardJson, datasetSchemaMap);
      console.log(JSON.stringify(result, null, 2));
    } catch (e) {
      console.log(JSON.stringify({ success: false, error: e.message }));
      process.exit(1);
    }
  });
}

// 导出函数供 Node.js 使用
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { parseDashboardJson, analyzeLayout };
}
