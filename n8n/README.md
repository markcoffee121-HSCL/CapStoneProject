# n8n Integration (Webhook)

1. Open n8n → **Import** → select `flow-export.json`.
2. The Webhook URL will be:
   - Cloud: `https://<your-subdomain>.n8n.cloud/webhook/hscl/report`
   - Local: `http://localhost:5678/webhook/hscl/report`
3. Put the URL into your project's `.env` as `N8N_WEBHOOK_URL=<...>`.
4. (Optional) Verify signatures:
   - Set `N8N_SECRET=...` in `.env`.
   - In n8n, add a **Function** node before Slack/Email to verify `X-HSCL-Signature`.
5. Add your actions:
   - **Slack**: add “Slack → Post Message” and connect from Webhook to Slack (and also to Respond).
     - Message idea:
       ```
       *HSCL Report — {{$json.topic}}*  (run {{$json.run_id}})
       Model: {{$json.model}} | Provider: {{$json.search_provider}}
       {{ $json.report_md.slice(0, 1500) }}
       Top Sources:
       {{ $json.sources.join('\n') }}
       ```
   - **Email**: use SMTP node with `{{$json.report_md}}` as body (HTML mode).
   - **Google Drive**: “Upload” with a Binary node if you also send the file contents.
