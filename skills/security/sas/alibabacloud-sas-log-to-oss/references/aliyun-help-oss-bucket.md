The OSS Management Console is a simple and easy-to-use web-based OSS management tool provided by Alibaba Cloud. With this tutorial, you can complete basic operations such as creating a bucket, uploading files, and sharing files within 10 minutes, with an estimated cost of less than 0.01 CNY.

## Prerequisites

-   You have [registered an Alibaba Cloud account](https://account.aliyun.com/register/qr_register.htm?oauth_callback=https%3A%2F%2Fbailian.console.aliyun.com%2F%3FapiKey%3D1).

-   You have completed [individual real-name verification](https://help.aliyun.com/zh/document_detail/324614.html#task-2020003) or [enterprise real-name verification](https://help.aliyun.com/zh/account/overview).

-   You have [activated OSS service](https://oss.console.aliyun.com/overview).

    > Purchasing an OSS resource plan does not automatically activate OSS. You still need to manually activate the OSS service, and activating OSS is free of charge.


## Step 1: Create a Bucket

A bucket is a container for storing files. Before using OSS, you need to create a bucket first.

1.  Navigate to the **Bucket List** page in the left sidebar and click **Create Bucket**.

2.  Configure the following key parameters, keeping the rest as defaults:

    -   **Bucket Name**: Enter a globally unique name. To ensure uniqueness, it is recommended to use a combination of **project name - region - random string**, for example `my-project-hangzhou-a1b2c3d4`.

    -   **Region**: Select a region close to you, such as China (Hangzhou), to reduce access latency.

3.  Click **Confirm**.


## Step 2: Upload a File

After creating a bucket, you can upload various types of files (objects) such as images, videos, and documents to it.

> You can upload files up to 5 GB in a single operation through the console. For larger files, it is recommended to use the [command-line tool ossutil](https://help.aliyun.com/zh/oss/command-line-tools-ossutil-quickstart).

1.  If you do not have a suitable test file locally, you can first download this example file [exampleobject.jpg](https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240926/tajhik/exampleobject.jpg) to your local machine.

2.  On the **Bucket List** page, click the name of the bucket you just created.

3.  Navigate to **Files** > **File List** in the left sidebar, then click **Upload File**.

4.  Drag the local exampleobject.jpg file to the **Files to Upload** area, or select the file via **Scan Files**.

5.  Keep other parameters as default and click **Upload File**.


You can view the upload progress of each file in the **Upload List** tab. After the upload is complete, you can view the file name, file size, and storage type under the target path.

## Step 3: Download a File

Files in a bucket can be downloaded to your local machine.

1.  On the **File List** page, find the exampleobject.jpg file you just uploaded.

2.  Check the file, then click the **Download** button below the list.


## Step 4: Share a File

Files in a private bucket can be shared by generating a time-limited secure link (URL).

1.  On the **File List** page, click the file name of `exampleobject.jpg`.

2.  In the **Details** panel that appears on the right, you can optionally set the **Expiration Time (seconds)** of the link (default is 600), then click **Copy File URL**.

    -   > **Cost:** This URL uses the public endpoint. Any download through this URL will incur **public network outbound traffic fees**.

    -   > **Security:** Before sharing, please ensure the file does not contain any sensitive data.

    -   > **Expiration:** The URL will automatically expire after the set validity period. To access it again, you need to regenerate the URL.

3.  Paste the copied URL into your browser's address bar to access it. The default behavior is to download the image file directly. If you want to preview the image in the browser, you need to [bind a custom domain name](https://help.aliyun.com/zh/oss/user-guide/access-buckets-via-custom-domain-names#1e43238a95bb6) and use the custom domain name to generate the URL.


## Step 5: Cleanup

To prevent files from incurring ongoing charges, you need to first delete all files in the bucket, then delete the bucket itself. **Deletion is irreversible**.

### **Delete Files**

1.  In the left sidebar, select **Files** > **File List**.

2.  Check the uploaded example file exampleobject.jpg.

3.  Click **Permanently Delete** below the list, and click **OK** in the popup.


### **Delete the Bucket**

> After deleting a bucket, you need to wait several hours (usually 4 to 8 hours) before you can create a bucket with the same name again.

1.  On the **Bucket List** page, click the name of the bucket you want to delete.

2.  In the left sidebar, click **Delete Bucket**.

3.  Click **Delete Now**, and follow the console prompts to complete the remaining steps.


## Billing Description

The OSS billing items involved in this tutorial mainly include:

-   **Storage fee**: While files are stored, standard storage fees will continue to be incurred.

-   **Public network outbound traffic fee**: When others download files using the shared link (URL), public network outbound traffic fees will be incurred.

-   **Request fee**: Upload and download operations will incur API request count fees.


The total cost of completing this tutorial (uploading a file smaller than 1 MB and downloading it once) is estimated to be **less than 0.01 CNY**. For pricing details, see [OSS Product Pricing](https://www.aliyun.com/price/product?spm=a2c4g.11186623.0.0.628c4d22ZdP2B0#/oss/detail/oss).

## **Next Steps**

-   **In-depth Cost Management:** Learn about billing details through [Billing Overview](https://help.aliyun.com/zh/oss/billing-overview), and save costs with [Resource Plans](https://help.aliyun.com/zh/oss/resource-plan/).

-   **Automation:** Learn the [SDK Quick Start](https://help.aliyun.com/zh/oss/user-guide/oss-sdk-quick-start) to manage OSS via code in your applications.

-   **More File Operations:** Check the [Feature Guide](https://help.aliyun.com/zh/oss/user-guide/object-overview#a47cf1e035u7e) for more ways to manage files.

-   **Strengthen Data Security:** Fine-tune data access permissions by configuring [Permissions and Access Control Overview](https://help.aliyun.com/zh/oss/user-guide/permissions-and-access-control-overview).

    **Note**

    When creating a bucket through the OSS console, [Block Public Access](https://help.aliyun.com/zh/oss/user-guide/block-public-access) is enabled by default. Once enabled, you cannot create public access permissions, including public-read or public-read-write ACLs, and bucket policies with public access semantics. If your business requires public access, you can disable Block Public Access after creating the bucket.


## **FAQ**

-   [Usage Query](https://help.aliyun.com/zh/oss/usage-query/)

-   [Objects/Files (Object)](https://help.aliyun.com/zh/oss/data-upload-and-download/)

-   [Resource Plans](https://help.aliyun.com/zh/oss/package-faq/)
