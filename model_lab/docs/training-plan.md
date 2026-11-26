# Training Plan: Video, Speech, and Voice Models

Draft, November 2026. Prices and licences come from public sources checked this month; confirm them before spending money.

## 1. Goal

Own the parts of the stack that make our videos recognisable:

- **Our presenter** looks the same in every scene and moves in our story style (video LoRA).
- **Our voices** read Vietnamese naturally, in several accents and voice types (speech fine-tune plus voice conversion).

We fine-tune open models instead of training from scratch. Training a video or speech foundation model needs far more data and compute than we can justify; fine-tuning adds our character and voices on top of a model that already knows how to make video and speech.

## 2. Base models (licence gate)

| Task | Model | Licence | Status for a paid product |
|---|---|---|---|
| Video | Wan 2.1 T2V 1.3B | Apache-2.0 | Allowed. Use for the pilot. |
| Video | Wan 2.1 T2V 14B, Wan 2.2 T2V A14B | Apache-2.0 | Allowed. Use for production. |
| Video | LTX-Video, HunyuanVideo | Conflicting or conditional | Blocked until checked |
| Speech (vi) | MeloTTS-Vietnamese | MIT (model card) | Allowed. Default. |
| Speech (vi) | VieNeu-TTS v3 Turbo | Apache-2.0 per a third-party listing | Blocked until the LICENSE file is checked |
| Speech (vi) | F5-TTS Vietnamese checkpoints | CC-BY-NC-SA-4.0 | Not allowed (non-commercial) |
| Speech (vi) | viXTTS | Based on XTTS-v2, non-commercial | Not allowed |
| Speech (en) | MeloTTS English | MIT | Allowed |
| Voice conversion | OpenVoice v2 | MIT (not re-verified) | Blocked until checked |
| Voice conversion | Applio (RVC) | MIT per README; asks commercial users to contact them | Blocked until checked |
| Voice conversion | Seed-VC | GPL-3.0 weights per a derivative's card | Blocked until checked |

The tools enforce this table (`configs/models.yaml`). To unblock a model, read its LICENSE file and model card, then set `commercial_ok: yes` with a note of what you checked.

Sources: [VieNeu-TTS listing](https://aitoolradar.io/open-source/vieneu-tts), [F5-TTS Vietnamese ViVoice](https://huggingface.co/hynt/F5-TTS-Vietnamese-ViVoice), [MeloTTS-Vietnamese](https://huggingface.co/nmcuong/MeloTTS-Vietnamese), [open video model licences](https://morphic.com/resources/tools/best-open-source-ai-video-models), [Seed-VC derivative card](https://huggingface.co/ayyappanallamothu4/suryaseedvc), [Applio](https://github.com/ayutaz/Applio).

## 3. How each capability is built

### 3.1 Character video LoRA (Fox first)

- **Data:** 100 to 300 short clips (2 to 5 seconds, 9:16) of our presenter, rendered from the 3D character rig, in each pose and with each prop. Captions describe the action and always include the trigger phrase ("mntr fox" for the launch character).
- **Trainer:** musubi-tuner (kohya-ss). Its documentation recommends 24 GB or more of GPU memory for video training ([musubi-tuner](https://github.com/kohya-ss/musubi-tuner)). Wan 2.2 A14B trains separate high-noise and low-noise models.
- **Step 0, available now:** an image dataset from the official Fox sheets: 24 figures (6 poses, 4 turnaround views, 6 expressions, 8 mouth shapes) on 5 backgrounds, 120 captioned images (`python -m modellab image-data`). It trains appearance only, and carries the small face drift in the concept sheets, so treat the result as a pipeline test. It stays research-only until OpenAI's terms are confirmed for training and commercial use.
- **Pilot first:** Wan 2.1 1.3B, to prove the data and pipeline cheaply. Then Wan 2.2 A14B for quality.
- **Gate:** in a 20-scene test set, the presenter must be recognisably the same in at least 90% of scenes (human review plus VLM checklist), with no distorted faces.

### 3.2 Speech fine-tune

- **Data:** about 60 minutes of clean speech per speaker to start (adjust after the pilot). Recorded in a quiet room, 24 kHz mono, 1 to 15 seconds per clip, transcripts checked.
- **Trainer:** MeloTTS (multi-speaker). One model per language; each speaker is an accent and voice type.
- **Normalisation:** every transcript goes through the Vietnamese normaliser with the speaker's dialect, so training text and inference text match.
- **Gate:** word error rate measured with Whisper is no worse than the base model on 50 test sentences, and at least 10 native listeners per accent rate it natural and correctly accented.

### 3.3 Voice types through conversion

- **Data:** 10 minutes of reference audio per voice type, from a consenting adult voice actor.
- **Method:** speak with the right accent using the speech model, then convert the timbre to the voice type.
- **Gate:** listeners must still hear the original accent after conversion; if the accent drifts, record that voice type directly instead (method `tts_speaker`).

## 4. Data needs from the current voice plan

From `configs/voices.yaml`:

| Item | Count | Data per item | Total |
|---|---|---|---|
| Speakers recorded for accent and voice (`tts_speaker`) | 10 | about 60 minutes of clean speech | about 10 hours |
| Voice types by conversion (`vc_timbre`) | 5 | about 10 minutes of reference audio | about 50 minutes |
| Presenter video clips | 1 character | 100 to 300 clips | about 5 to 25 minutes of video |

Recording usually takes 2 to 3 times the length of usable audio once retakes and editing are counted. That is a planning assumption, not a measured figure.

## 5. Compute and cost (estimates)

| Job | GPU | Hours (estimate) | Cost |
|---|---|---|---|
| Video LoRA pilot (Wan 1.3B, about 100 clips) | 24 GB card | about 4 | depends on provider |
| Video LoRA production (Wan 2.2 A14B) | 80 GB (e.g. H100) | about 10 | about $19 at $1.89/h |
| Speech fine-tune per language | 24 GB card | about 8 | depends on provider |
| Evaluation runs | 24 GB card | about 2 per round | depends on provider |

The $1.89 per hour H100 figure is one rate quoted in a November 2026 price comparison found during research; it has not been checked with a provider. All hours are estimates to replace with measured figures after the first run. `plan.json` records the estimate for each job once `gpu.hourly_usd` is filled in.

Training compute is small compared with the other costs. The main costs are voice actors, studio time, the 3D character, and engineering time.

## 6. Phases

| Phase | Weeks | Work | Exit gate |
|---|---|---|---|
| 0. Tools | done | This project: data checks, licence and consent gates, normaliser, job files, eval | 52 tests pass |
| 1. Legal and setup | 1 to 2 | Confirm licences; voice actor contract covering training, conversion, and commercial use; rent GPU | Contract approved by a lawyer; licences confirmed |
| 2. Speech pilot | 2 to 5 | Record 2 speakers (north male, south female); fine-tune MeloTTS-Vietnamese; evaluate | Speech gate in 3.2 |
| 3. Video pilot | 3 to 6 | Render 100 presenter clips from the 3D rig; Wan 1.3B LoRA; evaluate | Video gate in 3.1 |
| 4. Voice types | 5 to 8 | Confirm a conversion model's licence; 10 min reference per voice type; evaluate accent preservation | Voice gate in 3.3 |
| 5. Production models | 7 to 12 | Wan 2.2 A14B LoRA; remaining speakers; connect to the Short Video Studio app as providers | Cost per second and quality meet the business plan |

## 7. Risks

| Risk | Mitigation |
|---|---|
| A base model's licence changes or is misread | Licence gate; record what was checked and when; re-check before each release |
| Voice misuse or cloning without consent | Consent ledger enforced by the tools; no real-person cloning; disclosure on outputs; consider audio watermarking later |
| Child voices | Adult actors only; no recordings of minors |
| Accents judged wrongly by non-native reviewers | Native listeners for each accent in every evaluation |
| MeloTTS-Vietnamese fork quality or maintenance | Pilot first; keep VieNeu-TTS as the alternative once its licence is confirmed |
| Trainer flags change between versions | Pin the trainer version; generated scripts say which version they target |
| Character drifts in generated video | Reference-image conditioning; video gate; fall back to rendered scenes |

## 8. Decisions needed

1. Approve the voice plan in `configs/voices.yaml` (which accents and voice types to offer first).
2. Budget for voice actors and studio time (about 10 hours of clean speech for the full plan; 2 hours for the pilot).
3. GPU provider and budget.
4. Who confirms licences and drafts the voice actor contract.
