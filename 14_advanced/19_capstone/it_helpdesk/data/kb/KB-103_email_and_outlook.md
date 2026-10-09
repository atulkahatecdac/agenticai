# KB-103: Email and Outlook

BrightPath uses Microsoft 365 (Outlook, Teams, OneDrive).

## Outlook is not receiving new email

1. Check the status of the Email service first. If it is degraded, wait - do not
   raise a ticket.
2. Check the bottom bar of Outlook: if it says "Working offline", click
   Send/Receive -> Work Offline to turn offline mode off.
3. Close Outlook, then open it again.
4. Try Outlook on the web (`outlook.office.com`). If email works there, the
   problem is the desktop app: repair it from Settings -> Apps -> Microsoft 365 -> Modify -> Quick Repair.

## Mailbox full

- The standard mailbox size is **50 GB**.
- Empty "Deleted Items" and move old mail to the Online Archive (right-click a
  folder -> Archive).
- Mailbox size increases are not provided; use the Online Archive instead.

## Shared mailboxes

Access to a shared mailbox (for example `finance-team@`) is a **restricted**
access request and needs the mailbox owner's manager to approve it. See POL-201.

## Suspicious email

Do not click links or open attachments. Use the "Report Phishing" button in
Outlook. If you already clicked a link or entered your password, treat it as a
security incident - see POL-203.
