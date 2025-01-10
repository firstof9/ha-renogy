# renogy

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

_Component to integrate with [Renogy][renogy] connected products._

**This component will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | On/Off sensors for various settings.
`sensor` | Show info from an Renogy's API.

## Obtaining your Renogy API Keys

You will require two keys to use this integration. The keys can be obtained at Renogy's deveopler platform here:

https://platform.renogy.com/

Once you are logged in, click on your name at the top right, and click on "API Key". From here, click on "Create New Key". The first key that will be shown is your secret key or the key that starts with `sk`.  Copy paste this key because it only shows it once. Then, when you press ok, it shows you the second key or the access key or `ak` key. You can always go back and see the ak key but not the sk key. If you lose or forget the sk key, just delete it and make a new one.

You can make more than one set of keys, if you wish.

Please note that the email associated with your API account must be the same email that your hub is paired to. You can check this in the hub settings. Also, only devices that are paired to the hub will be exposed to the Renogy API (i.e.e devices that are connected to the DC Home App or older Renogy apps, will not be exposed to the API).

## Installation via HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=firstof9&repository=ha-renogy&category=integration)

1. Follow the link [here](https://hacs.xyz/docs/faq/custom_repositories/)
2. Use the custom repo link https://github.com/firstof9/ha-renogy
3. Select the category type `integration`
4. Then once it's there (still in HACS) click the INSTALL button
5. Restart Home Assistant
6. Once restarted, in the HA UI go to `Configuration` (the ⚙️ in the lower left) -> `Devices and Services` click `+ Add Integration` and search for `renogy`

## Manual (non-HACS)
<details>
<summary>Instructions</summary>
  
<br>
You probably do not want to do this! Use the HACS method above unless you know what you are doing and have a good reason as to why you are installing manually
<br>
  
1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `renogy`.
4. Download _all_ the files from the `custom_components/renogy/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. Once restarted, in the HA UI go to `Configuration` (the ⚙️ in the lower left) -> `Devices and Services` click `+ Add Integration` and search for `renogy`
</details>

## Configuration is done in the UI

<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

## TODO

- [ ] Add tests
- [ ] Code


[renogy]: https://renogy.com/
[integration_blueprint]: https://github.com/firstof9/ha-renogy
[buymecoffee]: https://www.buymeacoffee.com/firstof9
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/firstof9/ha-renogy.svg?style=for-the-badge
[commits]: https://github.com/firstof9/ha-renogy/commits/main
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/firstof9/ha-renogy.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Chris%20Nowak%20%40firstof9-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/firstof9/ha-renogy.svg?style=for-the-badge
[releases]: https://github.com/firstof9/ha-renogy/releases
