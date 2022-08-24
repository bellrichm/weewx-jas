# weewx-jas

A WeeWX skin that uses [Apache ECharts](https://echarts.apache.org/en/index.html) to chart the data.
The following javascript libraries are used in addition to Apache ECharts.

- [bootstrap](https://getbootstrap.com/)
- [popper](https://popper.js.org/)
- [moment](https://momentjs.com/)
- [vanilla-datetimerange-picker](https://github.com/alumuko/vanilla-datetimerange-picker)
- [pahoo-mqtt](https://www.eclipse.org/paho/index.php?page=clients/js/index.php)

## Installation notes

Because there are [multiple methods to install WeeWX](http://weewx.com/docs/usersguide.htm#installation_methods), location of files can vary.
See [where to find things](http://weewx.com/docs/usersguide.htm#Where_to_find_things)
in the WeeWX [User's Guide](http://weewx.com/docs/usersguide.htm") for the definitive information.
The following symbolic names are used to define the various locations:

- *$DOWNLOAD_ROOT* - The directory containing the downloaded *weewx-jas* extension.
- *$BIN_ROOT* - The directory where WeeWX executables are located.
- *$CONFIG_ROOT* - The directory where the configuration (typically, weewx.conf) is located.

The notation vX.Y.Z designates the version being installed.
X.Y.Z is the release.

Prior to making any updates/changes, always make a backup.

## Preqrequisites

|WeeWX version   |Python version                               |
|----------------|---------------------------------------------|
|4.6.0 or greater|Python 3.5 or greater                        |

## Installation

1. Download weewx-jas

    ```
    wget -P $DOWNLOAD_ROOT https://github.com/bellrichm/weewx-jas/archive/vX.Y.Z.tar.gz
    ```

    All of the releases can be found [here](https://github.com/bellrichm/weewx-jas/releases) and this is the [latest](https://github.com/bellrichm/weewx-jas/releases/latest).

2. Install weewx-jas

3. Restart WeeWX

    ```
    sudo /etc/init.d/weewx restart
    ```

    or

    ```
    sudo sudo service restart weewx
    ```

    or

    ```
    sudo systemctl restart weewx
    ```

## Manual Installation

See, [manual installation](https://github.com/bellrichm/weewx-jas/wiki/Manual-installation).

## Customizing

Once the base installation is working see,
[customizinf](https://github.com/bellrichm/weewx-jas/wiki/Customizing) for information on how to customize the skin.

## Debugging

See, [debugging](https://github.com/bellrichm/weewx-jas/wiki/Debugging).

## Getting Help

Feel free to [open an issue](https://github.com/bellrichm/weewx-jas/issues/new),
[start a discussion in github](https://github.com/bellrichm/weewx-jas/discussions/new),
or [post on WeeWX google group](https://groups.google.com/g/weewx-user).
When doing so, see [Help! Posting to weewx user](https://github.com/weewx/weewx/wiki/Help!-Posting-to-weewx-user)
for information on capturing the log.
And yes, **capturing the log from WeeWX startup** makes debugging much easeier.
