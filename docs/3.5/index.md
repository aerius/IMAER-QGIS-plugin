* [Index](index.md)
* [Import Calculator Results](01_import_calc_results.md)
* [Extract GML from AERIUS PDF](03_extract_gml_from_pdf.md)
* [Generate Calculator Input](04_generate_calc_input.md)
* [Relate Calculator results](05_relate_calc_results.md)
* [Connect - Receptor Sets](07_connect_receptor_sets.md)
* [Connect - Jobs](08_connect_jobs.md)
* [Configuration](09_configuration.md)

# IMAER Plugin
The IMAER plugin for QGIS provides a set of tools for working with your AERIUS
IMAER data.

![imaer toolbar](img/imaer_plugin_toolbar.png)

## Functionality

The current functionality covers:
* Opening AERIUS Calculator results
* Extracting GML data from AERIUS PDF files
* Generating AERIUS Calculator input from your own emission source layers
* Performing calculations on Calculation result layers
* Perform operations on the AERIUS Connect API

## Installation

### From the QGIS plugin repository

The plugin is regularly updated in the QGIS plugin repository, so the easiest way
to install it is by using the Plugin Manager within QGIS. Currently you will need to
enable 'experimental plugins' to find it. The most recent plugin requires QGIS version
3.16.x or higher.

### From zip file

In case you want to use another version of the plugin than the most current in the QGIS plugin repository, you can download the desired plugin form github
[code](https://github.com/aerius/IMAER-QGIS-plugin)
and install it with the Plugin Manager in QGIS ("Install from zip tab").

### From python code

Of course you can also clone the code from the github repository and install it
manually in QGIS.

## Issues

If you meet any issues with this plugin, please file a bug report on the
github [issues](https://github.com/aerius/IMAER-QGIS-plugin/issues) page.
You can also suggest ideas for improvements or enhancements.

## License

This program is free software. You can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation. Either version 2 of the License, or
(at your option) any later version.
