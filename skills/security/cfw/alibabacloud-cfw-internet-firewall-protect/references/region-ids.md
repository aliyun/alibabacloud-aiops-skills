# Region IDs

Map commonly used regional labels to Alibaba Cloud region IDs before passing a
region filter. Region IDs are numbered within a geography rather than globally;
do not pass the localized label itself to the API.

```text
"华东1" (Hangzhou)       -> cn-hangzhou
"华东2" (Shanghai)       -> cn-shanghai
"华北1" (Qingdao)        -> cn-qingdao
"华北2" (Beijing)        -> cn-beijing
"华北3" (Zhangjiakou)    -> cn-zhangjiakou
"华北5" (Hohhot)         -> cn-huhehaote
"华北6" (Ulanqab)        -> cn-wulanchabu
"华南1" (Shenzhen)       -> cn-shenzhen
"华南2" (Heyuan)         -> cn-heyuan
"华南3" (Guangzhou)      -> cn-guangzhou
"西南1" (Chengdu)        -> cn-chengdu
```

For example, use `cn-beijing` for the Beijing label and `cn-shanghai` for the
Shanghai label.
