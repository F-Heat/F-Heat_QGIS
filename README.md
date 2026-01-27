# F|Heat - Heat Planning Plugin for QGIS

<img src="docs/images/fheat_logo.png" alt="FHeat Logo" width="300">

## Description
The Heat Planning Plugin for [QGIS](https://qgis.org/) enables functions like status analysis and heat network analysis for municipal heat planning. This plugin facilitates municipal heat planning by giving users access to various Python libraries within QGIS without the need for programming skills. The spatial resoultion of the plugin is currently tailored to North Rhine-Westphalia (NRW) located in Germany.

## Table of Contents
1. [Features and Usage](#features-and-usage)
2. [Quick-Start](#quick-start)
3. [Requirements](#requirements)
4. [Documentation](#documentation)
5. [Contact Information](#contact-information)
6. [Contributing](#contributing)
7. [License](#license)
8. [Acknowledgements](#acknowledgments)

## Features and Usage

This tool simplifies the urban heat planning process by automating tasks such as:
* downloading data, 
* customising necessary files,
* displaying suitable heat network areas and 
* a potential network layout.

The resulting network areas and routes (streets) can be customised and adjusted during the whole process. The process is about designating the planning region and is based on the [german heat planning law](https://www.gesetze-im-internet.de/wpg/BJNR18A0B0023.html).

## Quick-Start

If you do not have QGIS installed, you can download it from the official website: [qgis.org](https://qgis.org/download/)

Once QGIS is installed, open QGIS Desktop.
<img src="docs/images/readme/qs0.png" alt="quick start0" width="800">

Click on "Plugins" > "Manage and Install Plugins..."
<img src="docs/images/readme/qs1.png" alt="quick start1" width="800">

Select "All", search for "FHeat" and install the Plugin.
<img src="docs/images/readme/qs2.png" alt="quick start2" width="800">

If the plugin toolbar is not visible, right-click on an empty space in the toolbar and check the "Plugin Toolbar" box.
<img src="docs/images/readme/qs3.png" alt="quick start3" width="800">

The plugin toolbar with the F|Heat icon will then become visible.
<img src="docs/images/readme/qs4.png" alt="quick start4" width="800">

It is advisable to save the project before starting F|Heat, as the plugin utilizes the project directory to save files. The project can be saved by clicking the save icon or by selecting "Project" > "Save As...".
<img src="docs/images/readme/qs5.png" alt="quick start5" width="800">

F|Heat starts by clicking the icon in the toolbar. From there, the plugin guides you through the process. Check the documentation for a detailed example.
<img src="docs/images/readme/qs6.png" alt="quick start6" width="800">

## Requirements
For using the application as a plugin you need QGIS on your machine. The required Python packages are installed by using the plugin on your local machine.
Alternatively you can install the packages yourself by following this guide on [Installing Python packages in QGIS 3.](https://landscapearchaeology.org/2018/installing-python-packages-in-qgis-3-for-windows/)

## Documentation

All necessary steps are documented within the plugin. A detailed documentation about installation, usage and methodology is available via the following links:

[F|Heat ReadtheDocs](https://f-heat-qgis.readthedocs.io/en/latest)

[Official german website](https://www.fh-muenster.de/de/iep/fheat/index)

[QGIS plugin store](https://plugins.qgis.org/plugins/FHeat_QGIS/)

## Contributing

We welcome contributions from the community. Issues and Pull Requests for further development are greatly appreciated. To contribute follow this guideline:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them with descriptive messages.
4. Push your changes to your forked repository.
5. Open a pull request to the main repository.

Please ensure that your contributions align with the coding standards and consider to add tests for new functionalities. If you've never contributed to an open source project before we are more than happy to walk you through how to create a pull request.

## Contact Information
**F|Heat** is developed and maintained by FH Münster - University of Applied Sciences.

<img src="docs/images/readme/fh_logo.png" alt="FH Logo" width="350">

For further information, questions or feedback, please contact our development team: fheat@fh-muenster.de

## License

**F|Heat** is licensed under the GPL 3.0 License. We refer to the `LICENSE` file for more information.

## Acknowledgments

Credits to those who helped or inspired the project.

## Additional Attribution
This project uses code from the project [demandlib](https://github.com/oemof/demandlib) published under MIT license.
