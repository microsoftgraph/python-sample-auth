# Configuring the Python authentication samples

This page covers how to set up Python authentication samples for Microsoft Graph. These instructions apply to the samples in these repos:

## Prerequisites

Before installing the samples:

* Install Python from [https://www.python.org/](https://www.python.org/). We've tested the code with Python 3.6, but any Python 3.x version should work. If your code base is running under Python 2.7, you may find it helpful to use the [3to2](https://pypi.python.org/pypi/3to2) tools to port the code to Python 2.7.
* To register your application for access to Microsoft Graph, you'll need either a [Microsoft account](https://www.outlook.com) or an [Office 365 for business account](https://msdn.microsoft.com/en-us/office/office365/howto/setup-development-environment#bk_Office365Account). If you don't have one of these, you can create a Microsoft account for free at [outlook.com](https://www.outlook.com).

## Installation

Follow these steps to install the samples:

1. Clone the repo, using this command:
    * ```git clone https://github.com/microsoftgraph/python-sample-auth.git```
2. Create and activate a virtual environment (optional). If you're new to Python virtual environments, [Miniconda](https://conda.io/miniconda.html) is a great place to start.
3. In the root folder of your cloned repo, install the dependencies for the sample as listed in the ```requirements.txt``` file with this command: ```pip install -r requirements.txt```.

## Configuration

To configure the samples, you'll need to register a new application in the Azure portal [app registrations page](https://go.microsoft.com/fwlink/?linkid=2083908).

Follow these steps to register a new application:

1. Sign in to the Azure portal [app registrations page](https://go.microsoft.com/fwlink/?linkid=2083908) using either your personal or work or school account.

2. Choose **New registration** near the top of the page.

3. When the **Register an application** page appears, enter your application's registration information:
    * In the **Name** section, enter a meaningful application name that will be displayed to users of the app.
    * Change **Supported account types** to **Accounts in any organizational directory and personal Microsoft accounts (e.g. Skype, Xbox, Outlook.com)**.
    * Enter `http://localhost:5000/login/authorized` as the **Redirect URI**. The URI type should be **Web**.

4. Select **Register** to create the application.

5. The application's **Overview** page will display. On this page, find the **Application (client) ID** value and record it for later. You'll need it to configure the project.

6. Select **Certificates & secrets** under **Manage**.
    1. Select the **New client secret** button.
    2. Enter a value in **Description**.
    3. Select any option for **Expires**.
    4. When you click the **Add** button, the key value will be displayed. Copy the key value and save it in a safe location. You'll need it in the next step.

7. This sample only require the default **User.Read** permission, which is pre-selected for a new application registration, you won't need to add any additional permissions.

As the final step in configuring the sample, modify the ```config.py``` file in the root folder of your cloned repo, and follow the instructions to enter your Client ID (Application ID) and Client Secret. Then save the change, and you're ready to run the sample.

## Working with multiple samples

Samples that use Microsoft ADAL for authentication require that all required permissions/scopes are added to the application in the Application Registration Portal. So if you're using ADAL for multiple samples, you can either register a separate app for each sample, or add all required permissions to a single registered application.

Samples using the other auth options can take advantage of _incremental consent_, which means you don't need to add permissions to the application registration. You can edit the ```SCOPES``` setting in the ```config.py``` file to add any permissions required for each sample, and the user will be prompted to consent to these permissions with they log in to the sample app.
