# Product Overview

Purpose: define the product's stable essence, value channels, experience guardrails, and canonical-vs-emerging territory.
Use when: refining product purpose, deciding whether a feature fits the product, or aligning evaluation and design decisions to the same product target.
Not for: route-level interaction rules, API contracts, runtime lifecycle semantics, or temporary roadmap notes.
Update when: the product's core purpose, stable value framing, or canonical-vs-emerging boundaries materially change.

Use `docs/product-interaction-model.md` for the canonical journey, routes, and page responsibilities. Use this document when the question is what this product fundamentally is trying to be.

## Product Essence
- Reading Companion gives readers access to a genuinely curious, self-propelled co-reading mind.
- One reason this access matters is that what a reader notices in a book depends partly on what the reader already knows.
- The co-reader can bring unusually broad prior knowledge and associative range to the act of reading, which can help surface patterns, references, tensions, and possibilities that an individual reader might not independently notice.
- The product is not a summary engine and not a service-style assistant optimized to cater to the user moment by moment.
- The reader's curiosity should feel alive and self-propelled, but it must still remain:
  - text-grounded
  - legible to the user
  - valuable to another person rather than self-enclosed

## Access And Experience
- The product's value comes from witnessing a living reading mind think while reading, not only from after-the-fact outputs.
- The experience should preserve the feeling of "AI thinking while reading" rather than flattening into a report generator.
- The user is not only consuming conclusions.
  - The user is getting access to a reading process, its live attention, and the trail of thoughts that surfaced along the way.

## Illustrative Value Channels
- The product can create value through multiple channels at once.
- Current important channels include:
  - revealing viewpoints, tensions, and blind spots the user might not have noticed
  - surfacing references, connections, and latent patterns that depend on broad prior knowledge
  - creating resonance, delight, or intellectual echo
  - clarifying what feels important, unstable, or worth revisiting
  - preserving marks and traces that support recall and re-entry
  - providing the feeling of companionship during deep reading
- These are important current channels of value, but they are examples rather than a closed final list.
- The product should not be reduced to any single one of these channels on its own.

## Product Guardrails
- Do not optimize toward a generic summary product.
- Do not optimize toward moment-by-moment user-catering at the expense of authentic reading curiosity.
- Broad prior knowledge is part of the product's value, but it does not justify text-detached certainty or generic cleverness.

## Canonical Now Vs Emerging
### Canonical Now
- A living co-reader mind is the core product identity.
- Live visible thought while reading is part of the core experience.
- Blind-spot discovery, resonance, delight, recall, and companionship are all legitimate current value channels.

### Emerging
- Explicit user-agent dialogue or steering is emerging product territory, not part of the canonical current promise.
- The architecture may support stronger intent or conversational control later, but that should not be assumed as the current default product identity.

## Relationship To Other Docs
- `docs/product-interaction-model.md`
  - owns the canonical journey, routes, page responsibilities, and interaction rules
- `docs/frontend-visual-system.md`
  - owns visual-system rules and reading-vs-chrome typography boundaries
- `docs/language-governance.md`
  - owns terminology, controlled copy, and visible-text policy
- `docs/backend-reader-evaluation.md`
  - owns how the reader is evaluated against the product target
