# Messages

Other services ask for a notification by publishing a message to RabbitMQ. This
page is the contract: a field's name and meaning never change within a
version. A change that would break a publisher is a new `version`, and the
old version keeps working until no publisher sends it.

## Publishing

- Exchange **`notifications`**: direct, durable. Declare it as such; the
  arguments must match.
- Routing key: the message's kind (below).
- Body: JSON, UTF-8. Properties: `content_type: application/json`,
  `delivery_mode: 2` (persistent), and `message_id` = the body's `id`.
- Publish with **publisher confirms** and **`mandatory`**. If the publish is
  confirmed, RabbitMQ stored the message, and it will be sent even if this
  service is down for a while. If the publish is returned unroutable, this
  service never declared its queue, which is an error to report.
- Don't declare this service's queues. They are its own, and their arguments
  must match exactly.

The identity service does this in
`app/infrastructure/notifications/rabbitmq.py`.

## `email.confirmation_code`, version 1

A confirmation code the identity service made, to email to the user.

```json
{
  "type": "confirmation_code",
  "version": 1,
  "id": "6f1c3b0e-2a5d-4e8f-9c71-0d2b6a4e9f13",
  "to": "player@example.com",
  "purpose": "verify_email",
  "code": "042137",
  "created_at": "2026-10-25T12:00:00.000000+00:00",
  "expires_in_minutes": 10
}
```

| Field | | |
|---|---|---|
| `type` | `"confirmation_code"` | |
| `version` | `1` | |
| `id` | string, 1–100 characters | unique per message (a UUID); it shows in this service's logs |
| `to` | email address | |
| `purpose` | `"verify_email"` or `"reset_password"` | chooses the email's words |
| `code` | six digits | shown as it is; this service never stores it |
| `created_at` | ISO 8601 date-time **with a timezone** | when the code was made |
| `expires_in_minutes` | integer, 1–1440 | how long the code works after `created_at` |

Other fields are ignored, so a publisher may add some.

What happens:
- **The email:** the subject is "`<code>` is your Balatro confirmation code"
  (or "… password reset code"), and the body comes as text and as HTML. It says
  how many minutes the code still works, counted from `created_at`: a message
  that waited for a retry says less.
- **An expired code:** a message whose code expired before it could be sent is
  dropped, with a warning in the log.
- **An invalid message** (another `version`, a bad address, a code that isn't
  six digits, a date without a timezone) is set aside at once, in the
  `notification.email.failed` queue.

## Adding a kind of message

1. A model in `app/presentation/messaging/schemas.py` (`type`, `version`, the
   fields).
2. A use case in `app/application/use_cases/` and a template in
   `app/infrastructure/templates/`.
3. Its `type` in `MessageHandler`, and its routing key in
   `app/infrastructure/rabbitmq/topology.py` (`ROUTING_KEYS`). Binding a new key
   to the existing queues is fine.
4. Its section on this page, then tests (handler, use case, template).
