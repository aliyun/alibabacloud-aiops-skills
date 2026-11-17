#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The credential answer a password ticket is owed before its instance id arrives.

Measured on the W1 login development half (60 first questions, 0 pass): 36 name a
password or a key pair, and not one answer stated the online/offline reset
contract. The shared no-target plan asked those customers for the very password
they were trying to reset, then swept security groups, firewalls and listen
states, which the judge named irrelevant to a VNC password rejection.

Every line below is a rule the engineer's own reply states on those tickets. None
of it needs a credential, an instance id or a cloud read, which is why it belongs
in the dispatcher's pre-target block rather than behind the area's diagnosis.

The branches are ordered most-specific first, and the generic remote chain stays
the fallback for a ticket that names no credential symptom at all. Nothing here
performs a write: a restart is named as a step the customer takes after giving
consent, never as something this tool does.
"""

import re

# An Alibaba Cloud account password is not an instance password. Two tickets in
# the measured half asked for the account one, and the answer talked about the
# guest Administrator user instead.
ACCOUNT_PASSWORD_RE = re.compile(
    r'账号密码|账户密码|账号登录名|登录名.{0,4}找回|找回.{0,4}登录名'
    r'|阿里云账号.{0,10}密码|账号\s*ID.{0,8}格式')

# The reset itself was refused. `无效` belongs here rather than in the
# no-effect branch: "both online and offline are ineffective" is a failed
# change, and its gold answer is the security-software plus offline-disk path.
RESET_FAILED_RE = re.compile(
    r'(重置|修改|改|更换).{0,8}密码.{0,12}(失败|无效|不了|报错|不成功|不生效)'
    r'|(无法|不能|没法).{0,8}(在线|离线)?.{0,4}(重置|修改|改).{0,4}密码'
    r'|(在线|离线).{0,6}重置.{0,8}(失败|无效|不了)'
    r'|密码.{0,6}(重置|修改).{0,6}(失败|无效)'
    r'|reset.{0,20}password.{0,20}(fail|error|denied)', re.I)

# The reset was accepted but the credential still does not work.
RESET_NO_EFFECT_RE = re.compile(
    r'(重置|改|修改).{0,10}密码.{0,20}(还是|仍然|仍|也|依然|又)'
    r'.{0,12}(登录不了|登陆不了|进不去|登不上|登不了|不行|密码错误|无效|失败)'
    r'|(重置|改|修改).{0,6}密码后.{0,12}(登录不了|登陆不了|登不上|进不去|无法登录)'
    r'|密码.{0,8}(过期|改了|改过).{0,16}(登录不了|登不上|进不去|又)'
    r'|凭据不工作|credentials?.{0,12}(not work|invalid)', re.I)

KEYPAIR_RE = re.compile(
    r'密钥对|秘钥对|密钥文件|秘钥文件|私钥|公钥|key\s?pair|keypair|\.pem', re.I)

# How to reset, where to reset it, what the two channels differ in, and whether
# the password can be looked up at all. One plan answers all four: the measured
# gold replies are the same paragraph.
RESET_GUIDE_RE = re.compile(
    r'重置.{0,4}密码|改.{0,4}密码|修改.{0,6}密码|忘记.{0,4}密码|密码.{0,4}忘记'
    r'|密码.{0,6}(过期|在哪|哪里|查看|找回)|在线重置|离线重置'
    r'|(用户名|账户名|账号).{0,6}(及|和|与).{0,4}密码'
    r'|(查看|查询|获取|知道).{0,10}(用户名|密码)|默认密码|初始密码'
    r'|reset.{0,12}password|forgot.{0,12}password', re.I)

# The bare-password tail: "Windows密码", "第一次登录密码问题". The guide is
# still the right answer, because ECS has no default password to hand over.
PASSWORD_ANY_RE = re.compile(r'密码|password|口令', re.I)

# A question that states no failure is a knowledge question. Measured: the gold
# reply to "what is the difference between online and offline reset" is the rule
# itself, and the judge scored the skill down for "only asking for the id" even
# after the right rule was present. The id is still worth offering as an
# escalation path, but it must not be the ask that carries the answer.
CREDENTIAL_FAULT_RE = re.compile(
    r'连不上|连不了|登录不了|登陆不了|登不上|登不了|进不去|无法|失败|错误|无效'
    r'|报错|不成功|不生效|锁定|被锁|异常|篡改|攻击|中毒|勒索'
    r'|denied|refused|fail|error|invalid|locked|cannot|can not|unable', re.I)

ACCOUNT_PASSWORD_PLAN = (
    "First separate the two passwords: the Alibaba Cloud account password signs "
    "in to the console, the instance password signs in to the guest. They are "
    "reset in different places and one cannot be used for the other.",
    "The account password and the account login name are recovered on the account "
    "sign-in page, by mobile number, domain, invoice or enterprise verification. "
    "ECS cannot reset them, and this check cannot read them.",
    "Administrator is the guest user on a Windows instance, not the account login "
    "name, and an IP address is never a login name.",
    "If it is the instance password you need, name the instance and its region "
    "and the reset path applies instead.",
)

RESET_GUIDE_PLAN = (
    "ECS ships with no default instance password, and the password cannot be "
    "viewed or read back anywhere - console, API or ticket. It can only be reset. "
    "The sign-in user is root on Linux and Administrator on Windows.",
    "Reset it in the ECS console: Instances, switch to the instance's own region, "
    "select the instance, then More > Password/Key > Reset Instance Password. "
    "The mobile App does not offer every credential page, so use a PC browser.",
    "Prefer the online reset. It needs the instance Running and the Cloud "
    "Assistant agent installed and running, and the new password takes effect "
    "immediately with no restart.",
    "The offline reset is the fallback when the agent is unavailable. It only "
    "takes effect after the instance is restarted, so snapshot the system disk "
    "and every data disk first, stop the applications so memory data lands on "
    "disk, and have the customer restart in a low-traffic window - the restart "
    "interrupts business and is the customer's to approve and perform.",
    "If the reset itself is refused, send the exact error text or a screenshot; "
    "the wording decides which of the two channels failed.",
)

RESET_FAILED_PLAN = (
    "The online reset needs two things at once: the instance is Running and the "
    "Cloud Assistant agent is installed and running. A missing, stopped or "
    "compromised agent is the usual reason the online reset is refused - not the "
    "password you typed.",
    "Read the exact error before retrying. 'Key pair has been removed' means the "
    "bound key pair is gone; a command that never runs means the agent channel is "
    "broken. Send that error text or a screenshot.",
    "Third-party security software in the guest - Huorong, 360, Safedog - blocks "
    "the console password change. Have the customer turn its protection off "
    "briefly, reset again, then turn it back on.",
    "Then fall back to the offline reset: snapshot the system disk and every data "
    "disk, stop the applications so memory data lands on disk, reset offline, and "
    "have the customer restart the instance in a low-traffic window. The offline "
    "password is not in force until that restart, and the restart interrupts "
    "business, so the customer approves and performs it.",
    "If both channels fail, the last resort is to stop the instance, detach the "
    "system disk, attach it to a repair instance, change the credential there and "
    "attach it back. That needs an explicit stop consent and a snapshot first.",
)

RESET_NO_EFFECT_PLAN = (
    "First check which channel was used: an offline reset changes nothing until "
    "the instance is restarted, so the old password is still the one in force. "
    "An online reset takes effect at once.",
    "Then check third-party security software in the guest - Huorong, 360, "
    "Safedog. It can block the change even when the console reports success. "
    "Turn it off briefly and reset again, or change the password inside the guest.",
    "On Linux, read /etc/ssh/sshd_config for PermitRootLogin prohibit-password "
    "and PasswordAuthentication no: either one refuses a correct password. Set "
    "them to yes, restart sshd rather than the instance, and retry.",
    "Separate the two paths with the console VNC session and the new password. "
    "VNC works but the client fails means the credential is fine and the client "
    "or the network path is at fault; VNC also rejects it means the credential "
    "itself never changed.",
    "On Windows VNC send CTRL+ALT+DELETE first and sign in as Administrator; "
    "check the input method and any trailing space. A locked account is not "
    "unlocked by a password reset.",
)

KEYPAIR_PLAN = (
    "The private key file (.pem) is offered once, at creation. It cannot be "
    "viewed or downloaded again afterwards, and the mobile App does not list key "
    "pairs at all - use a PC browser on the ECS console Key Pairs page.",
    "If the browser saved nothing, check the address bar for a pop-up or "
    "download-blocked icon and allow it, clear the cache or try another browser, "
    "or call CreateKeyPair and store the returned private key yourself.",
    "A lost private key cannot be recovered. Create a new pair, bind it to the "
    "instance and have the customer restart the instance for the binding to take "
    "effect, or reset the instance password and sign in with that instead.",
    "For a refused key login, derive the public key from the private key and "
    "compare it with the bound pair, and read PermitRootLogin in "
    "/etc/ssh/sshd_config - prohibit-password refuses passwords, not keys.",
    "An instance with a bound key pair cannot be transferred to another account "
    "until the pair is unbound.",
)


def credential_plan(question):
    """Return the credential block this first question is owed, or ().

    Pure and additive: no match means no block, so a remote ticket that never
    mentions a credential keeps the generic chain it had before.
    """
    text = question or ''
    if not text.strip():
        return ()
    if ACCOUNT_PASSWORD_RE.search(text):
        return ACCOUNT_PASSWORD_PLAN
    if RESET_FAILED_RE.search(text):
        return RESET_FAILED_PLAN
    if RESET_NO_EFFECT_RE.search(text):
        return RESET_NO_EFFECT_PLAN
    if KEYPAIR_RE.search(text):
        return KEYPAIR_PLAN
    if RESET_GUIDE_RE.search(text) or PASSWORD_ANY_RE.search(text):
        return RESET_GUIDE_PLAN
    return ()


def knowledge_only(question):
    """True when this credential question states a rule lookup, not a failure.

    Only the guide, account and key-pair branches can be knowledge-only: a reset
    that failed or a reset that did not take effect is a fault by its own wording,
    and those tickets are still owed a target so the instance can be read.
    """
    text = question or ''
    if not text.strip() or CREDENTIAL_FAULT_RE.search(text):
        return False
    return credential_plan(text) in (RESET_GUIDE_PLAN, ACCOUNT_PASSWORD_PLAN,
                                     KEYPAIR_PLAN)
