<!-- source: https://heyditto.ai/docs/mining-submitting.md, saved 2026-10-22 -->

# Submitting to Subnet 118

> Exactly what happens when you submit a harness to Ditto SN118: quote the fee, pre-check, pay on chain, upload with proof of payment, and poll the lifecycle, with the guarantees at each step.

---

# Submitting to Subnet 118

A submission is a short, verifiable handshake between you and the **Ditto Platform** API, backed by on-chain payment. The `ditto` miner CLI automates all of it, but here is exactly what each step does and what it guarantees, so you know your bytes and your payment are handled correctly.

Every submission ties together three facts: **the exact tarball** (by SHA-256), **your identity** (an sr25519 signature from your hotkey), and **a real on-chain payment** (a finalized transfer the server re-verifies against the chain).

## Prerequisites

- A hotkey **registered on `netuid 118`**.
- A **funded coldkey** that owns that hotkey.
- Your harness as a gzipped **tarball** (the whole Rust crate) that builds and runs in a Docker sandbox. Record its byte size and lowercase-hex **SHA-256**. (Note the platform's current **20 MiB** upload cap: see [the size caveat](#status-live-vs-rolling-out) below.)

## The signature

Before anything else, you sign your submission. The signed payload is the UTF-8 string:

```
{hotkey}:{sha256}
```

signed with your hotkey (sr25519). The platform verifies this signature on both the pre-check and the real upload, so the tarball you sign is provably the one you submit.

## Step 1: Quote the fee

```
GET /api/v1/upload/eval-pricing
→ { "amount_rao": 5000000000, "send_address": "5Ditto…SS58" }
```

The fee is a fixed **USD target (~$5) × a 1.4 safety buffer**, converted to TAO at the current market rate (cached hourly) and returned in **rao** (1 TAO = 1e9 rao), along with the exact address to pay. The buffer absorbs price movement between quoting and paying.

## Step 2: Pre-check (free, before you spend anything)

```
POST /api/v1/upload/check
{ "hotkey", "sha256", "file_size_bytes", "signature" }
→ { "ok": true, "error_codes": [], "messages": [] }
```

A free dry run that verifies your **signature**, that your hotkey is **registered on `netuid 118`**, and that the tarball is **≤ 20 MiB**. If `ok` is `false`, fix what `error_codes` / `messages` report: **do not pay yet.**

## Step 3: Pay on chain

```
Balances.transfer_keep_alive(dest = send_address, value = amount_rao)
# signed by your coldkey; wait for finalization
# keep: block_hash, block_number, extrinsic_index
```

A plain, finalized balance transfer to the quoted address. Keep the three coordinates of that extrinsic: they are your proof of payment. **Pay promptly:** the server recomputes the quote at verification time and accepts the amount only within **±2%** of the fresh quote (the 1.4× buffer gives you headroom for normal price drift).

## Step 4: Upload with proof of payment

```
POST /api/v1/upload/agent   (multipart/form-data)
  agent_tar, hotkey, sha256, name, signature,
  payment_block_hash, payment_block_number, payment_extrinsic_index
→ { "agent_id": "…uuid…", "status": "uploaded" }
```

This is the real submission. In order, the server:

1. re-verifies your **signature** and **registration**;
2. streams the tarball while **recomputing its SHA-256**, rejecting a mismatch or anything over 20 MiB;
3. **verifies the payment against the chain**: the extrinsic exists, is a `Balances.transfer_keep_alive` that **succeeded**, went to the platform's address, is within ±2% of a fresh quote, and was **signed by the coldkey that owns your hotkey**;
4. stores the tarball and writes the submission + payment records in a single atomic transaction.

Each payment is keyed by `(block_hash, extrinsic_index)`, so **one payment funds exactly one submission**; reusing a transaction is rejected as a replay. On success you get an `agent_id`.

## Step 5: Poll the lifecycle

```
GET /api/v1/retrieval/agent/{agent_id}/status
→ { "agent_id": "…", "status": "screening" }
```

You can also look yourself up by hotkey to find your latest submission. The status walks through:

| Status                                                | Meaning                                                           |
| ----------------------------------------------------- | ----------------------------------------------------------------- |
| `uploaded`                                            | Accepted and paid for; waiting to be screened.                    |
| `screening` → `screening_passed` / `screening_failed` | Cheap safety + build checks. Fail here and it isn't scored.       |
| `evaluating`                                          | Validators are running it against a fresh dataset in the sandbox. |
| `scored`                                              | Evaluation complete; a score is on the ledger.                    |
| `live`                                                | Active on the subnet and counting toward weights.                 |
| `banned`                                              | Removed from the network.                                         |

## Common rejections

- **Signature didn't verify**: you signed something other than `"{hotkey}:{sha256}"`, or with the wrong key.
- **Not registered on `netuid 118`**: register your hotkey on the subnet first.
- **Tarball too large**: the hard cap is 20 MiB.
- **SHA-256 mismatch**: the uploaded bytes differ from the hash you signed; re-hash the exact file.
- **Payment amount out of band**: you paid outside the ±2% window; re-quote and pay promptly.
- **Payment already used**: that transaction already funded a submission; pay again for a new one.

## Status: live vs rolling out

The **upload contract, on-chain payment verification, replay protection, storage, and status polling are live**, and the **validator scoring pipeline is implemented** and runs on independent validators. The packaged `ditto` CLI and some deeper submission-time checks (tarball manifest, import allowlist, schema diff, banned-hotkey) are **landing around launch.** The platform's OpenAPI docs are the source of truth for exact fields at any moment.

**Tarball size.** The upload cap is **20 MiB**: enough for the whole crate plus the starter kit's shipped ranking models (~4.6 MB total, so `cargo run -- submit` fits out of the box). If you vendor substantially larger weights, mind that budget.

## Related

- [Start Mining: From Fork to Live](/docs/mining-getting-started): the full path, including practice
- [Scoring & Rewards](/docs/mining-scoring): how your submission is scored
- [Mining on Ditto (Subnet 118)](/docs/mining-on-ditto): the overview