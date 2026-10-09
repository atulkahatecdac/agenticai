# KB-101: VPN Troubleshooting (GlobalProtect)

BrightPath Solutions uses the GlobalProtect VPN client on all company laptops.
There are two VPN gateways:

- **Pune gateway** - `vpn-pune.brightpath.example`
- **Mumbai gateway** - `vpn-mumbai.brightpath.example`

Both gateways give access to the same internal systems. If one gateway is down
or under maintenance, employees can switch to the other one.

## Before you troubleshoot

1. Check the IT service status page (or ask the helpdesk assistant) - if the VPN
   service is marked "degraded" or "down", the problem is on our side and a
   ticket is not needed unless the status message says otherwise.
2. Confirm you have a working internet connection by opening any public website.

## VPN does not connect at all

1. Quit GlobalProtect completely (right-click the tray icon -> Exit) and start it again.
2. Make sure the portal address is `portal.brightpath.example`.
3. If you see "Authentication failed", your password may have expired or your
   account may be locked - see KB-102.
4. Restart the laptop. This fixes most "connecting..." loops after a Windows update.

## VPN keeps disconnecting

1. Switch to the other gateway: GlobalProtect -> Settings -> Gateway -> choose
   the Mumbai or Pune gateway manually instead of "Best Available".
2. Avoid public Wi-Fi with captive portals (hotels, airports) - log in to the
   captive portal in a browser first, then connect the VPN.
3. If the drops continue on a stable home network for more than one day, raise a
   ticket with priority P3 and mention your laptop model and location.

## Switching gateways during maintenance

When a gateway is under planned maintenance, the status page names the gateway.
Select the other gateway manually as described above. You do not need to raise a
ticket for planned maintenance.

## When to raise a ticket

- VPN fails on both gateways after restarting the laptop: **P2** (you cannot work).
- VPN drops intermittently but you can still work: **P3**.
