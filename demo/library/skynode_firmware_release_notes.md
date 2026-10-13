# SkyNode Firmware Release Notes

Firmware updates download and install automatically, overnight, so they don't interrupt data
collection. Aurora releases updates roughly once a month. You can see a hub's firmware version
in the Aurora app under **Settings > Station > About**.

*Aurora Instruments is a fictional company created for demonstration and testing. All names,
figures and products are invented.*

## 4.6.0 (2 September 2026)

- **SkyNode Lite:** the data update interval can now be set to 30 seconds (the default stays
  60 seconds). A 30-second interval shortens sensor battery life by about 20%.
- **All models:** the app shows the estimated days left on each sensor's batteries.
- Fixed: rain totals could reset at midnight UTC instead of local midnight.

## 4.5.0 (14 July 2026)

- **SkyNode Max:** switches to cellular backup when Wi-Fi has been down for 2 minutes, instead
  of 10.
- **SkyNode Pro and Max:** lightning detection now estimates the strike distance (up to 40 km).

## 4.4.0 (19 May 2026)

- **All models:** a read-only local network API on the hub, for home-automation systems. It
  works without an AuroraLive plan and without an internet connection. (The cloud API still
  needs the Pro plan.)

## 4.2.0 (16 February 2026)

- **SkyNode Lite hardware revision B:** adds 5 GHz Wi-Fi. Revision B hubs have serial numbers
  starting **LB-** and have shipped since January 2026. Revision A hubs (serial numbers
  starting **LA-**) have a 2.4 GHz radio only and stay on 2.4 GHz.
- **All models:** faster pairing of replacement sensor modules.

## 4.0.0 (3 November 2025)

- New hub software platform. Hubs older than firmware 3.8 must be updated over USB-C once,
  following the steps in the Aurora app.
