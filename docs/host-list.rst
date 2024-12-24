.. source: https://gist.github.com/Twentysix26/cb4401c6e507782aa6698e9e470243ed

.. _host-list:

===================
Hosting Information
===================

.. note::
    This doc is written for the :ref:`hosting section <getting-started-hosting>`
    of the :ref:`getting started guide <getting-started>`. Please take a look
    if you don't know how to host Red.


| For your instance of Red to stay online 24/7, it needs to be hosted on a dedicated system.
  This page contains hosting related information and advice for beginners in 
  topics such as picking a provider.

First, we would like to make something clear:

.. warning::
    Due to their inability to handle Red's data structure and meet the
    conditions of being a supported platform; platforms such as Heroku, 
    Pterodactyl, repl.it, Termux and alike are **NOT** officially supported. 
    Docker support found in GitHub is also a work in progress and not ready
    for daily use. Workarounds for getting Red running on those platforms
    are imperfect due to Red's nature. You will not be able to receive
    support if an issue occurs when hosting on any of these platforms.


------------------------------------
Hosting on a VPS or Dedicated Server
------------------------------------

| You can host Red in a VPS running Linux or Windows. Using a Linux VPS is the
  recommended option. Dedicated servers also work but are overpowered and cost 
  ineffective unless one plans to run a very large bot or use their server for 
  more than just hosting Red. If you have already created an instance, Red can be moved to a different 
  server for hosting with a backup/restore process. More information and guidance
  about this process is available in the `Red Support Server <https://discord.com/invite/red>`_.

.. warning::
    Please be aware that a Linux server is controlled through a command line.
    If you don't know Unix basics, please take a look at
    `DigitalOcean's tutorial: An Introduction to Linux Basics
    <https://www.digitalocean.com/community/tutorials/an-introduction-to-linux-basics>`_.


------------
Self Hosting
------------

| It's possible to self host Red with your own hardware. A Raspberry Pi 3 
  will have enough computing capacity to handle a small to medium sized bot. 
  You can also host on your own computer or rack server. Any modern hardware 
  should work without issues. However, this option leaves you responsible for
  keeping the bot online by paying for electricity costs and dealing with power outages.

-------------------
Choosing a Provider
-------------------

| The following are some common providers suitable for hosting Red. With
  each having their pros and cons, this list is mainly intended to act as a
  starting point. You should conduct your own research and come to
  a conclusion depending on your needs and budget, taking into account
  providers not listed here if desired. The key is the provider offering 
  an OS supported by Red.

.. tip::
 You will have better results with Audio when the region in your Discord 
 server settings is closer to the bulk of the server's audience and
 the location you picked for your Red host.


-----------------
Average Providers
-----------------

| `Scaleway <https://www.scaleway.com/>`_ is a VPS and dedicated server
 provider French in origin with locations in Poland and Netherlands.

| `DigitalOcean <https://www.digitalocean.com/>`_ is a US based cloud services company 
 with locations available worldwide, the VPS service is provided under the brand name
 "Droplet".

| `OVH <https://us.ovhcloud.com/vps/>`_ is a company focused on providing hosting
 and cloud services with locations in Europe, North America and Asia Pacific.

| `Time4VPS <https://www.time4vps.eu/>`_ is a Lithuanian VPS provider mainly focused
 on lower cost.

| `GalaxyGate <https://galaxygate.net/>`_ is a VPS and dedicated server provider
 with a single location in New York.

| `Linode <https://www.linode.com/>`_ is a US based cloud services company similar
 to DigitalOcean with locations available worldwide.

| `AWS Lightsail <https://aws.amazon.com/lightsail/>`_ is a VPS service from Amazon
 Web Services priced lower than their enterprise offerings.

| `Vultr <https://www.vultr.com/>`_ is a US based provider of VPS and dedicated servers
 with locations available worldwide.

| `Hetzner Online <https://www.hetzner.com/>`_ is a German VPS and dedicated server
 provider with locations in Germany, US and Finland.

| `Contabo <https://contabo.com/>`_ is also a German VPS and dedicated server provider
 with locations in Germany, Asia, Australia and the United States.

| `Ramnode <https://www.ramnode.com/>`_ is a US based VPS provider focused on
 low to middle end VPS with locations in the US and Netherlands.

| `LowEndBox <http://lowendbox.com/>`_ is a website where hosting providers are
 discussed and curated, often with lower costs and less known providers.

| `AlphaVps <https://alphavps.com>`_ is a Bulgaria VPS and dedicated server provider 
 with locations in Los Angeles, New York, England, Germany and Bulgaria.

--------------------
Higher End Providers
--------------------

| `AWS EC2 <https://aws.amazon.com/ec2/>`__ is the enterprise offering of Amazon Web Services.
 A limited free plan is available for 12 months, after which a complex pricing model with
 high costs take over.

| `Google Compute Engine <https://cloud.google.com/compute/>`__ is Google's EC2 competitor.
 However, an always free plan with limited resources is offered.

| `Microsoft Azure VM <https://azure.microsoft.com/services/virtual-machines/>`__ is
 Microsoft's EC2 competitor with lower costs than EC2 for Windows instances, but similar
 otherwise.

| `Oracle Cloud Compute  <https://www.oracle.com/cloud/compute/>`__ is Oracle's EC2
 competitor. But an always free plan is available with slightly higher specifications
 compared to that of Google Compute Engine.

------------
Free Hosting
------------

| `Google Compute Engine <https://cloud.google.com/free/docs/gcp-free-tier>`_,
  `Oracle Cloud Compute <https://oracle.com/cloud/free/#always-free>`_ and
  `AWS EC2 <https://aws.amazon.com/free/>`_ have free tier VPSes suitable for small bots.

| **Note:** The free tier offered by AWS for EC2 only lasts for 12 months, while
 Oracle Cloud and Google Cloud offer always free tiers with limited resources.

| Additionally, new Google Cloud customers get a $300 credit which is valid for 3 months.
 New Oracle Cloud customers also get $300 of free credit, but only valid for 30 days.

| Excluding the above, there is no recommended free VPS host. Persuasion of
 another individual for hosting Red is an option, albeit low in success rate.
