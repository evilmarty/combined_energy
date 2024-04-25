# Combined Energy

## Description

Home Assistant integration for Combined Energy.

**Full Disclosure**

This code is a snapshot from [Pull Request](https://github.com/home-assistant/core/pull/81724) by [timsavage](https://github.com/timsavage). I have simply made his integration available via [HACS](https://hacs.xyz) whilst waiting for his PR to be accepted. At time of writing that does not appear to be any time soon, unfortunately.

## Installation

There are two ways this integration can be installed into [Home Assistant](https://www.home-assistant.io).

The easiest way is to install the integration using [HACS](https://hacs.xyz).

Alternatively, installation can be done manually by copying the files in this repository into the custom_components directory in the HA configuration directory:

1. Open the configuration directory of your HA configuration.
2. If you do not have a custom_components directory, you need to create it.
3. In the custom_components directory create a new directory called combined_energy.
4. Copy all the files from the custom_components/combined_energy/ directory in this repository into the combined_energy directory.
5. Restart Home Assistant
6. Add the integration to Home Assistant (see `Configuration`)

### Configuration

After you have installed the custom component (see above):

1. Goto the Configuration -> Integrations page.
2. On the bottom right of the page, click on the + Add Integration sign to add an integration.
3. Search for Combined Energy. (If you don't see it, try refreshing your browser page to reload the cache.)
4. Provide the same credentials that are used for https://athome.combined.energy (see [How to get my Installation ID]).
5. Click Submit so add the integration.

### How to get my Installation ID

Obtaining this value will require a little digging. All strategies require you to be logged into https://athome.combined.energy using your web browser on a PC. Ensure you have access to Development Tools or Development Mode in your browser. Search the web on instructions on how to do this for your web browser.

#### Strategy 1

This is the easiest way to get the installation ID. Upon logging in simply open your browser's Development Tools and view the Web/Javascript Console. You may have to refresh the browser after the Console is present. In the output there should be something along the lines of `installation received - XXXX`, where `XXXX` is your installation ID.

#### Strategy 2

Open your browser's Development Tools to the Network screen. Ensure results are filtered by "XHR/Fetch" or the equivalent. Begin navigating the site until you see a request to `/data-service/dataAccess/installation`. Once such a request has been made inspect (or preview) its response and look for the value for the property `installationId`.
