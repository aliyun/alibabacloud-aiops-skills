# DingTalk Bot Creation and Configuration Guide

> Reference: https://open.dingtalk.com/document/dingstart/build-dingtalk-ai-employees

## 1. One-Click Create OpenClaw Bot

### 1.1 Log in to Developer Console

1. Visit the [DingTalk Developer Console](https://open-dev.dingtalk.com/?spm=ding_open_doc.document.0.0.76f5585ctYRvEz&hash=%23%2F#/) and log in by scanning the QR code with DingTalk
2. Select an organization where you have developer permissions
3. If no organization is available, create a new one using the DingTalk mobile app

### 1.2 Create Bot

1. Under "App Development", click **Create Now** to one-click create an OpenClaw bot
2. In the "Create OpenClaw" dialog, fill in the bot info (name, description, icon), or use the defaults directly
3. Click **OK**

### 1.3 Obtain Client ID and Client Secret

After successful creation, the **Client ID** and **Client Secret** are displayed automatically. Save them for later use.

> Security reminder: Client ID and Client Secret are core credentials of the app. Keep them secure and never share them.

You can also find them later in the app's "Credentials & Basic Info" page.

> Important: The auto-created OpenClaw bot comes with the following permissions pre-granted — no manual application needed:
> - `Card.Streaming.Write` — AI Card streaming update
> - `Card.Instance.Write` — Interactive card instance write
> - `qyapi_robot_sendmsg` — Internal bot send message



## 2.How Use the DingTalk Bot

### Option A: Direct Chat

1. In the DingTalk search bar at the top, search for the bot name
2. Send a message to start chatting with the bot

### Option B: Group Chat

1. Open any DingTalk group chat (ensure the group's organization matches the bot's organization)
2. Go to **Group Settings** (top right) > **Bots**
3. Click **Add Bot**, search for your bot name, and add it
4. @mention the bot in the group to interact

> Note: Only published bots can be found when adding to a group. Make sure the app version is published first.

## Troubleshooting

If the bot does not respond to messages, check:

1. Confirm the OpenClaw DingTalk plugin is installed (`openclaw plugins install @dingtalk-real-ai/dingtalk-connector`)
2. Verify Client ID and Client Secret are configured correctly
3. Confirm permissions `Card.Streaming.Write`, `Card.Instance.Write`, and `qyapi_robot_sendmsg` are granted
4. Check that the bot message receiving address is correctly configured
5. Ensure port 18789 is open on the server
6. Ensure the app version is published

### Bot not found when adding to group?

1. The group's organization may differ from the bot's organization — use the correct group
2. The group may not be an internal group — convert it to an internal group
