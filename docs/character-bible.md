# Character Bible (v0.3): the Mentor Cast

Purpose: a fixed cast of five presenter characters, each owning one business or education topic. Every image, clip, and training example must follow this document. A fine-tuned model can only be as consistent as the references it learns from.

Status: concepts chosen (generated with ChatGPT), stored in `assets/character/concepts/`. **Launch decision: Fox first**; the other four follow as each topic proves itself. Final designs still need a 3D model per character and an IP check. The earlier flat-vector presenter (`assets/character/*.svg`, `app/illustrate.py`) stays as a fallback.

---

## 1. The cast at a glance

| Character | Topic (domain) | Role in stories | Personality | Signature prop | Suggested voice type |
|---|---|---|---|---|---|
| **Fox** | Marketing, sales, branding | The strategist | Smart, quick, persuasive, always honest | phone (social media) | presenter-male-warm |
| **Owl** | Education and learning skills; Business 101 basics | The teacher | Patient, wise, clear | book or pointer (new prop) | mentor-older-calm |
| **Raccoon** | Personal finance, budgeting, saving | The resourceful saver | Clever with money, practical, funny | coins (piggy bank later) | young-energetic |
| **Bear** | Investing and risk | The careful investor | Calm, protective, steady | chart_up | presenter-male-warm (deeper) |
| **Otter** | Teamwork, leadership, productivity, soft skills | The team player | Friendly, social, organised | checklist | presenter-female-bright |

Each video normally has one host, chosen by topic. Two characters can appear together for a story conflict, for example Raccoon wants to spend everything and Bear explains the risk.

## 2. Shared "uniform" (identical for the whole cast)

The shared outfit makes the five characters read as one series:

- navy suit jacket and trousers, white shirt, red tie
- brown leather shoes
- chestnut-brown swept hair (quiff)
- glasses
- stylised 3D toon render, soft fur or feathers, soft studio lighting
- light-blue reference background (about #97C7FD)
- the same six poses with the same expressions (section 4)

Each character adds one or two details so viewers can tell them apart instantly, even as a small thumbnail.

## 3. Characters

### 3.1 Fox — Marketing, sales, branding

- **Look:** red fox, taller and slimmer (about 1 head to 3 body height); orange fur (about #EA7930) with cream muzzle, ear insides, and tail tip (about #EAD2CC); big bushy tail
- **Distinct details:** grey waistcoat (about #7C6660), red pocket square, dark brown rounded-rectangle glasses
- **Topics:** content marketing, selling online, pricing, building a brand, social media
- **Rules:** foxes are often seen as sly, so this fox is always open and honest. No smirks or side-eyes, and never "trick the customer" stories. Keep it clearly different from well-known film foxes: no green shirts or loose ties

### 3.2 Owl — Education and learning skills

- **Look:** brown and cream feathers, yellow beak, large round dark-brown glasses, chunky round body, feathered "hands" with fingers
- **Distinct details:** feather tufts on the head under the quiff; round glasses larger than anyone else's
- **Topics:** how to learn, study methods, explaining concepts, business basics for beginners
- **Rules:** in Vietnamese folk belief an owl's call is a bad omen, so keep the owl warm and cheerful, never spooky, never at night scenes. Test with Vietnamese viewers before launch

### 3.3 Raccoon — Personal finance, budgeting, saving

- **Look:** grey-beige fur with a dark eye mask, striped grey-brown tail, round gold glasses, chunky body, brown belt
- **Distinct details:** face mask and striped tail
- **Topics:** budgeting, saving, avoiding debt, smart spending, side income
- **Rules:** the face mask can suggest a "bandit", so never use stealing, hiding money, or "free money" jokes. The raccoon is resourceful and honest

### 3.4 Bear — Investing and risk

- **Look:** warm caramel-brown soft fur (felt texture), round ears, round gold-brown glasses, the chunkiest body in the cast
- **Distinct details:** biggest, roundest silhouette; plush texture
- **Topics:** investing basics, risk, diversification, long-term thinking, market downturns
- **Rules:** "bear market" means falling prices. We use that on purpose: the bear is the cautious voice who explains risk and protects savings. It never promises returns or tells people what to buy

### 3.5 Otter — Teamwork, leadership, productivity

- **Look:** brown fur with a cream face, whiskers, thin gold round glasses, flat tail, compact body
- **Distinct details:** whiskers and flat tail; a slightly smaller height than the others
- **Topics:** working in teams, leading people, communication, productivity, using tools and AI at work
- **Rules:** consider making the otter female, so the cast is not all male. The outfit can switch the tie for a red scarf or bow while keeping the navy suit

## 4. Poses and expressions (same for every character)

Each pose needs at least 20 consistent images or clips per character for training.

| Pose | Used for | Key visual |
|---|---|---|
| idle | neutral explanation | standing, hands at sides, gentle smile |
| thinking | posing a question | one hand at the chin, looking up |
| pointing | introducing a point | one arm extended with open palm, open smile |
| happy | good result | both fists at chest height, eyes closed, big smile |
| worried | problem statement | both hands on cheeks, raised brows, open mouth |
| celebrate | call to action, ending | jumping, both fists raised, big open smile |

Fix from the concept sheets: the owl winks in the celebrate pose; the final design should use the open smile like the others.

## 5. Consistency checklist (per character)

A design passes only if all are true:

- [ ] Same glasses, hair, and outfit in all six poses
- [ ] Signature details present in every image (waistcoat for Fox, mask and striped tail for Raccoon, and so on)
- [ ] Recognisable at phone size (1080 x 1920, character about 40% of the frame height)
- [ ] Each pose understandable without text
- [ ] No expression that undermines trust (sly, smug, scary)
- [ ] Clearly distinct from existing well-known characters

## 6. What this means for training and cost

- **One trigger phrase per character** in captions, for example "mntr fox", "mntr owl", "mntr raccoon", "mntr bear", "mntr otter". The video LoRA can learn the whole cast at once, with each trigger selecting a character.
- **Data per character:** a turnaround (front, three-quarter, side, back), a mouth-shape sheet for talking, and about 180 posed images plus 100 to 300 short clips from its 3D model.
- **Cost:** the 3D models, references, and voice work scale with the number of characters. Five characters cost roughly five times one.
- **Launch plan:** Fox launches first (marketing, sales, branding). Its 3D model, references, voice, and video LoRA come first. Raccoon (personal finance) is the suggested second character; Owl needs an audience test before launch.

## 7. Open decisions

1. Which character follows the Fox (Raccoon suggested).
2. Names for each character (short, easy to say in Vietnamese and English).
3. Whether the otter (or another character) is female.
4. Who builds the 3D models (an artist is recommended).
5. OpenAI's terms for commercial use of the concept images, and an IP check of the final designs.
