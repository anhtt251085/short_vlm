# Model Lab

Training project for our own video and voice models:

1. **Text-to-video:** a LoRA on an open video model (Wan) that knows our presenter character and story style.
2. **Text-to-speech:** a fine-tuned speech model that reads Vietnamese (and English) naturally, in our voices.
3. **Voice diversity:** several accents (Northern, Central, Southern Vietnamese; US and UK English) and voice types (warm presenter, bright presenter, older mentor, energetic, cartoon character).

This folder is self-contained so it can move to its own repository later.

## What runs where

| Step | Where | Status |
|---|---|---|
| Licence gate for base models | any computer | built, tested |
| Consent and rights ledger | any computer | built, tested |
| Vietnamese text normalisation (numbers, money, dates, dialects) | any computer | built, tested |
| Speech dataset checks and export | any computer (ffmpeg) | built, tested |
| Video clip dataset checks and export | any computer (ffmpeg) | built, tested |
| Image dataset from character sheets (cut-out, shadow removal, new backgrounds, captions) | any computer | built, tested; first Fox dataset built |
| Voice matrix (accent x voice type: what is ready, what is missing) | any computer | built, tested |
| Training job files (configs + launch scripts) | any computer | built, tested; scripts not run |
| Training | GPU machine | not run; no GPU in this environment |
| Evaluation (CPU proxies, word error rate, VLM checklist) | any computer; Whisper optional | built, tested |

## How accent and voice type are produced

- **Accent** is learned from real recordings of speakers of that accent. Each speaker is one accent and voice type in a multi-speaker speech model.
- **Voice type** can come from the speaker's own recordings, or from voice conversion applied on top of speech that already has the right accent. Voice conversion changes the timbre; it does not change the accent.
- The Vietnamese normaliser follows the dialect, so numbers read the way that accent says them ("một trăm linh năm" in the north, "một trăm lẻ năm" in the south).

See `docs/training-plan.md` for the full plan, data needs, costs, and gates.

## Quick start

```bash
cd model_lab
pip install -r requirements.txt
python -m pytest -q tests
python -m modellab doctor
```

List base models and whether their licence allows commercial use:

```bash
python -m modellab models
```

Normalise Vietnamese text for speech:

```bash
python -m modellab normalize "Doanh thu tháng 4 đạt 1.250.000.000đ, tăng 24%" --dialect south
```

Build a speech dataset (CSV columns: `path,text,speaker_id,accent[,style]`):

```bash
cp configs/consent.example.yaml consent.yaml   # then fill in real signed consent records
python -m modellab audio-data --input recordings.csv --consent consent.yaml --out data/speech --fix
```

See which voices are ready and what is missing:

```bash
python -m modellab voices --consent consent.yaml --manifest data/speech/manifest.jsonl
```

Build a video dataset (CSV columns: `path,caption,source_id`; every caption must contain the trigger phrase from `configs/video_lora.yaml`):

```bash
python -m modellab video-data --input clips.csv --consent consent.yaml --out data/video --fix
```

Build an image dataset from character sheets (see `configs/fox_sheets.yaml`):

```bash
python -m modellab image-data --consent consent.yaml --out data/fox_images --mode research
```

This cuts each figure out of the sheet's flat background, removes floor shadows, places it on five backgrounds, and writes a caption per image. It runs in research mode until the rights to the concept images (generated with ChatGPT) are confirmed for commercial use.

Write training jobs for a GPU machine:

```bash
python -m modellab plan-tts --dataset data/speech
python -m modellab plan-video --dataset data/video
```

`plan-video` accepts either clips (`videos/`) or images (`images/`). Each writes `runs/<run_name>/` with the trainer config, `run.sh`, and `plan.json` (licence, data summary, cost estimate). Copy the folder to the GPU machine, set `MELO_DIR` or `MUSUBI_DIR`, check the flags against the pinned trainer version, and run `run.sh`.

Evaluate outputs:

```bash
python -m modellab eval-audio --wav out.wav --script "Giá 50k" --whisper small
python -m modellab eval-video --video out.mp4 --reference ../assets/character/idle.png --narration "A worried presenter" --pose worried --prop question
```

## Rules built into the tools

- **Licences:** in commercial mode, only models with a confirmed commercial licence can be planned. Non-commercial models (for example F5-TTS Vietnamese checkpoints and viXTTS) are blocked. Unverified ones are blocked until someone checks the licence file and sets `commercial_ok: yes`.
- **Consent:** every recording must belong to a speaker whose signed consent covers training (and commercial use in commercial mode). Revoked or expired consent is rejected. Every video clip must come from an asset with training rights.
- **Privacy:** `consent.yaml` holds personal data and is ignored by git. Keep it in secure storage.
- **No minors, no real-person cloning:** see `configs/voices.yaml`.

## Layout

```
configs/
  models.yaml           base models, licences, trainer settings
  voices.yaml           accents, voice types, and how each is produced
  consent.example.yaml  consent and rights ledger template
  video_lora.yaml       video LoRA run settings
  tts.yaml              speech fine-tune run settings
  fox_sheets.yaml       which Fox sheets, grid layouts, and captions make the image dataset
modellab/
  registry.py           licence gate
  consent.py            consent and rights checks
  textnorm_vi.py        Vietnamese normalisation with dialects
  audio_data.py         speech dataset checks and exports (LJSpeech, MeloTTS)
  video_data.py         clip dataset checks and export (musubi-tuner layout)
  image_data.py         character sheets to a captioned image dataset
  planners.py           training job files and the voice matrix
  eval_audio.py         audio checks, word and character error rate
  eval_video.py         character consistency proxies, VLM checklist
  __main__.py           command line
docs/training-plan.md   phases, data, compute, costs, gates, risks
tests/                  60 tests using synthetic audio, video, and character sheets
```
