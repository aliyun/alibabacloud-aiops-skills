# OS and runtime support facts

These are the statements this tier can make about "which runtime installs on
which release", and the actions each one licenses. Everything here comes from
this tier's own ticket dialogues; where a ticket produced no official statement,
that absence is the answer given, and no support matrix is invented.

## Release-level facts

| Release | Fact | What to do with it | Evidence |
|---|---|---|---|
| Alibaba Cloud Linux 3 | the console one-click deployment scripts target this release | one-click deployment is applicable; verify the release before telling a customer a product is unsupported | T-F51E65E5 |
| Alibaba Cloud Linux 4 LTS 64-bit | `docker-ce` is not supported by default on this release; the supported container runtime is `moby` | install moby for Docker capability instead of troubleshooting the `docker-ce` installation | T-A9825E98 |
| Windows Server | Linux-oriented one-click deployment scripts do not apply | guide the manual installation path from the help catalogue instead of reporting the product as unsupported | T-F51E65E5, T-10715A07 |
| Windows Server, .NET Framework 3.5 install failure | a conflicting cumulative patch can block the .NET Framework 3.5 installation through Cloud Assistant | point at the public-image known-issues page for the patch removal path; removal plus a reboot is manual, and a snapshot must exist beforehand. The exact patch number in the ticket was only visible in a screenshot, so do not quote a patch id | T-BA3E2F89 |
| Alibaba Cloud Linux 4 LTS 64-bit with MongoDB 8.0 Community | there is no official compatibility statement for this combination | report "no official statement" verbatim; never invent a support matrix | T-A9825E98 |
| Rocky Linux 10 with a Python 3 default interpreter | automation written against Python 2 syntax fails on it while succeeding on older images | ask for the script body before naming a cause: forcing the interpreter did not help in the ticket, the Python 2 print statement did | T-8D57CDFD |
| SQL Server 2008 on a current Windows release | the operating system version no longer supports that product version | state the incompatibility and stop; there was no workaround in the ticket | T-BA3E2F89 |

## How to use these without overreaching

**Check the release before naming an unsupported product.** The most common
wrong answer in this tier was "this product is not supported", delivered before
anyone read the image id. `DescribeInstances` gives the OS name and image id in
one automatic call, so the premise is cheap to verify and the correction is
usually the whole answer.

**A default that does not exist is not a broken install.** On the release where
`docker-ce` is not supported, the customer's installation failure has no amount
of troubleshooting it can resolve; the runtime that provides the capability is a
different package. Name the substitute, and stop treating the failure as a bug.

**"No official statement" is a complete answer.** Where a combination is not
covered by any compatibility page, say exactly that. Do not extrapolate from a
neighbouring version, and do not present an installation attempt as verified.

**Windows failures split into two very different cases.** A manual installation
path simply has more steps; a patch conflict has one specific known cause whose
fix changes system state and needs a snapshot and a reboot. Only the second one
is a fault at all.

**An interpreter mismatch hides inside the customer's own automation.** When a
script fails on a newer image and passes on an older one, the interpreter is the
plausible suspect, and the decisive evidence is the script body, not the
interpreter override. One ticket showed the override failing while a Python 2
print statement was the actual cause.

## Open questions this file does not answer

- A compatibility page for `moby` versus Docker CE on the release above: not
  verified, so no URL is quoted for it.
- A MongoDB-on-ECS compatibility statement: not verified.
- Whether the customer's own vendor image carries the same defaults as the
  public image: never assumed here; the release is read from the instance.

Anything beyond these lines needs a source this package does not yet hold, so it
is asked about rather than asserted.
