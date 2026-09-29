# ANU Quantum Numbers setup

Oracle runs on Vercel. AWS Marketplace handles payment for ANU Quantum Numbers;
Oracle does not need AWS compute resources or AWS access keys.

## Subscription and activation

1. Sign into the intended existing AWS account and open the
   [ANU Marketplace listing](https://aws.amazon.com/marketplace/pp/prodview-246kyrfjo3bag).
2. Review the purchase options and vendor agreement before subscribing.
   Published pricing checked September 29, 2026: $0.005 per request,
   usage billed through AWS, cancel any time, no refunds. This is an ongoing
   usage subscription, without a spending cap.
3. Follow Marketplace's vendor setup link to ANU, sign into or create an ANU
   account, and complete the subscription linkage. On ANU's API Keys page,
   require **Plan: PAID, Status: ACTIVE**. If only a FREE key appears after
   signing up, return to AWS's purchase confirmation and click **Set up your
   account** again while signed into ANU. This completed the paid-key activation
   in the September 29, 2026 setup. Use the PAID key, not the separate FREE key;
   a trial account has only 100 requests per calendar month.
4. Add `ANU_QRNG_API_KEY` as a **Secret** in the Vercel `oracle` project's
   Production and Preview environments. Keep the key out of chat, source control,
   screenshots, and command arguments. Redeploy each environment that needs it.

ANU becomes the first provider automatically with the default order
`anu,lfdr,qrandom,anu_legacy`. Check any existing `QRNG_PROVIDERS` override before
deployment. See [ANU pricing](https://quantumnumbers.anu.edu.au/pricing) and
[API documentation](https://quantumnumbers.anu.edu.au/documentation).

## Verification

For a local provider check, put the key in the gitignored `.env` or supply it
through the process environment, then run with the installed project dependencies:

```sh
python3 scripts/check_anu.py
```

This makes exactly one ANU request using the application's endpoint, response
validation, and two-second timeout. It prints only status and latency. Exit 0
means ANU returned valid data; 1 means a provider failure; 2 means no key.
It never falls back and does not call Gemini. A local success does not verify
Vercel deployment configuration or the account's paid entitlement.

The paid API's `hex16` blocks use `size=2` for eight hex digits (32 bits),
confirmed against the live paid service on September 29, 2026. The legacy
endpoint uses `size=4` for the same width. These provider-specific sizes must
remain separate; requesting `size=4` from the paid service returns 16 hex digits
and causes the existing 32-bit validator to reject a successful response.

After redeploying, complete a test reading on the relevant Vercel deployment and
inspect its `qrng_result` runtime event. Require `provider: "anu"`,
`http_status: 200`, `source: "quantum"`, and `fallback_values: 0`.
A completed reading alone is insufficient because fallback providers can serve it.
Confirm paid subscription activation separately on the ANU account.

## Operations

- Consider a $25 monthly budget alert scoped to this Marketplace product; at the
  published rate that is approximately 5,000 requests. AWS budget alerts notify
  after usage is recorded; they do not impose a hard spending limit. Do not
  replace another project's existing budgets. Set the intended alert recipient
  explicitly.
- Provider failures are logged without questions, readings, keys, or random
  values. Failed providers have a 60-second cooldown on a warm instance.
- To remove ANU from new draws, set `QRNG_PROVIDERS=lfdr,qrandom,anu_legacy` and
  redeploy. This does not cancel Marketplace billing; cancel the subscription
  separately if retiring the service.
- The documented ANU API response has no cryptographic signature. Operational
  provenance logs do not establish a signed quantum receipt.
