# KB-104: Office Wi-Fi and Printing

## Office Wi-Fi

| Network | Who uses it | Notes |
|---|---|---|
| `BP-Corp` | Company laptops | Connects automatically using your laptop certificate. No password. |
| `BP-Guest` | Visitors, personal phones | Password is printed at reception. Internet only, no internal systems. |

**Company laptop cannot join BP-Corp:**

1. Turn Wi-Fi off and on again.
2. "Forget" the BP-Corp network and reconnect.
3. If the laptop was not connected to the office network or VPN for more than
   **60 days**, its certificate has expired. Connect to VPN once from home or
   plug into a wired office port, then restart - the certificate renews itself.

Never connect a company laptop to `BP-Guest` to work around a problem.

## Printing

- Printers are added automatically. Use "Follow-Me Print": print to the queue
  `BP-FollowMe`, then tap your ID badge on any office printer to release the job.
- Jobs not released within **24 hours** are deleted.
- Paper jams and toner: contact the floor's facilities desk, not IT.
- If your badge is not recognised by the printer, raise a P4 ticket.
