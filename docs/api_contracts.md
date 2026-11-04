# API verification log

Checked official sources on 2026-11-04. Documentation verification does not mean a
credentialed request succeeded. No credentials were supplied at build time.

* Meta Responses: https://dev.meta.ai/docs/protocols/responses
  POST `/v1/responses`, model + input, user input_text/input_image content blocks;
  input_image.image_url is a string data URL. Text comes from output message
  output_text blocks. `store: false` is sent. Default model muse-spark-1.3.
* Meta vision: https://dev.meta.ai/docs/image-understanding
  Inline base64 image data is documented for Responses and Chat (different shapes).
* Baseten: https://www.baseten.co/library/muse-spark-open/
  OpenAI-compatible `/v1/chat/completions`, Bearer key, messages, response choices.
  IMPORTANT discrepancy: public Meta/Baseten docs show `meta-models/muse-spark-open`.
  The requested dashboard-specific `meta-models/muse-spark-open-1026` is retained
  when Baseten is configured, as instructed, but was NOT verified in public docs.
  Confirm model entitlement and exact base URL in your dashboard. No silent alias.
* Voice: https://github.com/meta-models/meta-model-cookbook/tree/main/06_muse_voice/01_voice_api_fundamentals
  HTTP recording endpoint `/v1/asr/transcribe`, model muse-voice-transcribe-1.0.
  Checked cookbook utils.py: multipart `request` part is JSON with `model`,
  `mode: PUSH_TO_TALK`, `audioEncoding: WAV`; separate `audio` part holds the WAV.
  Bearer Authorization header; response `transcript` string. Mono 16-bit PCM
  WAV at 16 or 24 kHz. Local app restricts to 120 seconds / 10 MB (stricter than
  provider 10 minutes / 32 MB). Live execution remains unverified.

Live provider behavior, available models, account access and key validity remain
unverified until check_api is run with real credentials. Provider errors never
silently become mock successes.
