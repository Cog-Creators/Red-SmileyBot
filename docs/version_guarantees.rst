.. _version-guarantees:

==========
Versioning
==========

Red is versioned as ``major.minor.micro``

While this is very similar to SemVer, we have our own set of guarantees.

Major versions are for project wide rewrites and are not expected in the foreseeable future.

.. _end-user-guarantees:

===================
End-user Guarantees
===================

Red `provides support for wide variety of operating systems <install_guides/index>`.

Support for an entire operating system (including support for any single architecture on that system)
may only be dropped in a minor or major version bump.

Red will continue to, at the very least, support current latest stable version of
each operating system + architecture that were supported by previous micro versions.

In addition to that, we strive (but do not guarantee) to provide support for all versions that
are currently supported by operating system's developers per the table below.
We generally drop support for no longer supported OS versions as soon as they reached
their end-of-life date.

.. note::

    We recommend to always use the latest OS version supported by Red.

.. tip::

    The meaning of architecture names:

    - **x86-64** (also known as amd64) refers to computers running a 64-bit version of the operating system
      on standard Intel and AMD 64-bit processors supporting x86-64-v2 instruction set
      (post-2008 Intel processors and post-2011 AMD processors).
    - **aarch64** (also known as arm64) refers to computers running an ARM 64-bit version of the operating system
      on 64-bit ARM processors (ARMv8-A and ARMv9-A) such as Apple M1 devices or Raspberry Pi computers
      (Raspberry Pi 3B and above, excluding Pi Zero (W/WH) model).
    - **armv7l** (also known as armhf) refers to computers running an ARMv7 version of the operating system
      on 32-bit or 64-bit ARM processors (ARMv7-A, ARMv8-A, ARMv9-A) such as Raspberry Pi computers
      (2B and above, excluding Pi Zero (W/WH) model).

================================   =======================   ============================================================
Operating system version           Supported architectures   Ideally supported until
================================   =======================   ============================================================
Windows 10                         x86-64                    2025-10-14 (`End/Retirement Date <https://docs.microsoft.com/en-us/lifecycle/products/windows-10-home-and-pro>`__)
Windows 11                         x86-64                    `Retirement Date <https://docs.microsoft.com/en-us/lifecycle/products/windows-11-home-and-pro-version-21h2>`__
macOS 13 (Ventura)                 x86-64, aarch64           ~2025-10
macOS 14 (Sonoma)                  x86-64, aarch64           ~2026-10
macOS 15 (Sequoia)                 x86-64, aarch64           ~2027-10
Alma Linux 8                       x86-64, aarch64           2029-05-31 (`How long will CloudLinux support AlmaLinux? <https://wiki.almalinux.org/FAQ.html#how-long-will-almalinux-be-supported>`__)
Alma Linux 9                       x86-64, aarch64           2032-05-31
Amazon Linux 2023                  x86-64, aarch64           2028-03-15 (`end-of-life <https://docs.aws.amazon.com/linux/al2023/release-notes/support-info-by-support-statement.html#support-info-by-support-statement-eol>`__)
Arch Linux                         x86-64                    forever (support is only provided for an up-to-date system)
CentOS Stream 9                    x86-64, aarch64           2027-05-31 (`expected EOL <https://centos.org/stream9/#timeline>`__)
Debian 12 Bookworm                 x86-64, aarch64, armv7l   ~2026-09 (`End of life <https://wiki.debian.org/DebianReleases#Production_Releases>`__)
Fedora Linux 40                    x86-64, aarch64           2025-05-28 (`End of Life <https://docs.fedoraproject.org/en-US/releases/lifecycle/#_maintenance_schedule>`__)
Fedora Linux 41                    x86-64, aarch64           2025-11-19 (`End of Life <https://docs.fedoraproject.org/en-US/releases/lifecycle/#_maintenance_schedule>`__)
openSUSE Leap 15.5                 x86-64, aarch64           2024-12-31 (`end of maintenance life cycle <https://en.opensuse.org/Lifetime#openSUSE_Leap>`__)
openSUSE Leap 15.6                 x86-64, aarch64           2025-12-31 (`end of maintenance life cycle <https://en.opensuse.org/Lifetime#openSUSE_Leap>`__)
openSUSE Tumbleweed                x86-64, aarch64           forever (support is only provided for an up-to-date system)
Oracle Linux 8                     x86-64, aarch64           2029-07-31 (`End of Premier Support <https://www.oracle.com/us/support/library/elsp-lifetime-069338.pdf>`__)
Oracle Linux 9                     x86-64, aarch64           2032-06-31 (`End of Premier Support <https://www.oracle.com/us/support/library/elsp-lifetime-069338.pdf>`__)
Raspberry Pi OS (Legacy) 11        armv7l                    ~2025-10 (approximate date of release of Raspberry Pi OS 13)
Raspberry Pi OS 12                 aarch64, armv7l           ~2025-10 (approximate date of release of Raspberry Pi OS 13)
RHEL 8 (latest)                    x86-64, aarch64           2029-05-31 (`End of Maintenance Support <https://access.redhat.com/support/policy/updates/errata#Life_Cycle_Dates>`__)
RHEL 8.8                           x86-64, aarch64           2025-05-31 (`End of Extended Update Support <https://access.redhat.com/support/policy/updates/errata#Extended_Update_Support>`__)
RHEL 8.10                          x86-64, aarch64           2029-05-31 (`End of Extended Update Support <https://access.redhat.com/support/policy/updates/errata#Extended_Update_Support>`__)
RHEL 9 (latest)                    x86-64, aarch64           2032-05-31 (`End of Maintenance Support <https://access.redhat.com/support/policy/updates/errata#Life_Cycle_Dates>`__)
RHEL 9.2                           x86-64, aarch64           2025-05-31 (`End of Extended Update Support <https://access.redhat.com/support/policy/updates/errata#Extended_Update_Support>`__)
RHEL 9.4                           x86-64, aarch64           2026-04-30 (`End of Extended Update Support <https://access.redhat.com/support/policy/updates/errata#Extended_Update_Support>`__)
Rocky Linux 8                      x86-64, aarch64           2029-05-31 (`end-of-life <https://rockylinux.org/download/>`__)
Rocky Linux 9                      x86-64, aarch64           2032-05-31 (`end-of-life <https://rockylinux.org/download/>`__)
Ubuntu 20.04 LTS                   x86-64, aarch64           2025-06-30 (`End of Standard Support <https://wiki.ubuntu.com/Releases#Current>`__)
Ubuntu 22.04 LTS                   x86-64, aarch64           2027-06-30 (`End of Standard Support <https://wiki.ubuntu.com/Releases#Current>`__)
Ubuntu 24.04 LTS                   x86-64, aarch64           2029-06-30 (`End of Standard Support <https://wiki.ubuntu.com/Releases#Current>`__)
================================   =======================   ============================================================

.. _developer-guarantees:

====================
Developer Guarantees
====================

Any name (function, class, attribute) listed in the ``__all__`` attribute of
the ``redbot`` module (excluding its submodules), ``redbot.core`` package,
or any of its public submodules (modules that do not start with "_")
is considered a public API and should not break without notice.

Methods of public classes are considered public if they do not start with "_"
or are dunder methods (e.g. ``method()`` and ``__getattr__()`` are public but ``_method()`` isn't).

Any other name (function, class, attribute) in the ``redbot`` package is considered private,
even if it doesn't start with "_".
Lack of ``__all__`` in the module means that all of its names are considered private APIs.

Anything in the ``redbot.cogs`` and ``redbot.vendored`` modules or any of their submodules is specifically
excluded from being guaranteed.

Method names and names of attributes of classes, functions, extensions, and modules
provided by or provided to the bot should not begin with 
``red_`` or be of the form ``__red_*__`` except as documented.
This allows us to add certain optional features non-breakingly without a name conflict.

Any RPC method exposed by Red may break without notice.

If you would like something in here to be guaranteed,
open an issue making a case for it to be moved.

.. _developer-guarantees-exclusions:

Exclusions
----------

Any exclusion from these guarantees should be noted in the documentation of
the affected attribute, function, class, or method. The term "provisional"
may be used in documentation to note such exclusions.

.. _breaking-change-notices:

=======================
Breaking Change Notices
=======================

Breaking changes in Red will be noted in the changelog with a special section.

Breaking changes may only occur on a minor or major version bump.

A change not covered by our guarantees may not be considered breaking for these purposes, 
while still being documented as a breaking change in internal documentation
for the purposes of other internal APIs.
