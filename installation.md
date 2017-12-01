# Installing the Python REST samples

This page covers how to install Python REST samples for Microsoft Graph. These instructions apply to the samples in these repos:

* [Python authentication samples for Microsoft Graph](https://github.com/microsoftgraph/python-sample-auth)
* [Working with paginated Microsoft Graph responses in Python](https://github.com/microsoftgraph/python-sample-pagination)
* [Sending mail via Microsoft Graph from Python](https://github.com/microsoftgraph/python-sample-send-mail)

## Prerequisites

Before installing the sample:

* Install Python from [https://www.python.org/](https://www.python.org/). We've tested the code with Python 3.6, but any Python 3.x version should work. If your code base is running under Python 2.7, you may find it helpful to use the [3to2](https://pypi.python.org/pypi/3to2) tools to port the code to Python 2.7.
* To register your application for access to Microsoft Graph, you'll need either a [Microsoft account](https://www.outlook.com) or an [Office 365 for business account](https://msdn.microsoft.com/en-us/office/office365/howto/setup-development-environment#bk_Office365Account). If you don't have one of these, you can create a Microsoft account for free at [outlook.com](https://www.outlook.com).

## Installation

Follow these steps to install the samples:

1. Clone the repo, using one of these commands:

    ```git clone https://github.com/microsoftgraph/python-sample-auth.git```
    ```git clone https://github.com/microsoftgraph/python-sample-pagination.git```
    ```git clone https://github.com/microsoftgraph/python-send-mail.git```

2. Create and activate a virtual environment (optional). If you're new to Python virtual environments, [Miniconda](https://conda.io/miniconda.html) is a great place to start.
3. In the root folder of your cloned repo, install the dependencies for the sample as listed in the ```requirements.txt``` file with this command: ```pip install -r requirements.txt```.

## Configuration

To configure the samples, you'll need to register a new application in the Microsoft [Application Registration Portal](https://apps.dev.microsoft.com/).

Follow these steps to register a new application:

1. Sign in to the [Application Registration Portal](https://apps.dev.microsoft.com/) using either your personal or work or school account.

2. Under **My applications**, choose **Add an app**. If you're using an Office 365 account and see two categories listed (Converged or Azure AD only), choose **Add an app** for the Converged applications section.

3. Enter an application name, and choose **Create**. (Do *not* choose **Guided Setup**.)

4. Next you'll see the registration page for your app. Copy and save the **Application Id** field.You will need it later to complete the configuration process.

5. Under **Application Secrets**, choose **Generate New Password**. A new password will be displayed in the **New password generated** dialog. Copy this password. You will need it later to complete the configuration process.

6. Under **Platforms**, choose **Add platform** > **Web**.

7. Under **Delegated Permissions**, add the permissions/scopes required for the sample, as covered in the sample's README. For example, the [send mail](https://github.com/microsoftgraph/python-sample-send-mail) sample requires **Mail.Read** permission. Some samples (such as the [auth samples](https://github.com/microsoftgraph/python-sample-auth)) only require the default **User.Read** permission, which is pre-selected for a new application registration, so for those you won't need to add any permissions.

8. Enter `http://localhost:5000/login/authorized` as the Redirect URL, and then choose **Save**.

As the final step in configuring the sample, modify the ```config.py``` file in the root folder of your cloned repo, and follow the instructions to enter your Client ID and Client Secret (which are referred to as Application Id and Password in the app registration portal). Then save the change, and you're ready to run the samples as covered in each sample's README.

## Working with multiple samples

If you're installing multiple Python REST samples, you can re-use the application registration and ```config.py``` file in most cases.

Samples that use Microsoft ADAL for authentication require that all required permissions/scopes are added to the application in the Application Registration Portal. So if you're using ADAL for multiple samples, you can either register a separate app for each sample, or add all required permissions to a single registered application.

Samples using the other auth options can take advantage of _incremental consent_, which means you don't need to add permissions to the application registration. You can edit the ```SCOPES``` setting in the ```config.py``` file to add any permissions required for each sample, and the user will be prompted to consent to these permissions with they log in to the sample app.
