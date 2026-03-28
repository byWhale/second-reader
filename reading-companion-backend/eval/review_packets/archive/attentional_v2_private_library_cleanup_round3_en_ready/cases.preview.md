# Revision/Replacement Packet `attentional_v2_private_library_cleanup_round3_en_ready`

This packet was generated automatically from cases whose current `benchmark_status` requires another hardening round.

## Dataset
- dataset_id: `attentional_v2_private_library_excerpt_en_v2`
- family: `excerpt_cases`
- language_track: `en`
- version: `2`
- targeted_statuses: `needs_revision|needs_replacement`

## Review Actions
- `keep`
- `revise`
- `drop`
- `unclear`

## Confidence
- `high`
- `medium`
- `low`

## 1. `evicted_private_en__17__seed_2`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `Evicted`
- author: `Matthew Desmond`
- chapter: `Chapter 8: Christmas in Room 400` (`17`)
- question_ids: ``
- phenomena: ``
- selection_reason: 
- judge_focus: 
- latest_review_action: `revise`
- latest_problem_types: `ambiguous_focus|weak_excerpt`
- latest_revised_bucket: ``
- latest_notes: This case has critical metadata gaps (empty case_title, question_ids, phenomena, selection_reason, judge_focus) that make it unusable as a benchmark case. The excerpt mixes Rent Recovery Service's systemic debt collection critique with an Arleen courtroom scene without coherent focus. Needs either: (1) extract systemic debt collection analysis with proper metadata, or (2) frame the Arleen scene as specific case study with defined focus.

```text
Like landlords docketing judgments, the company took the long view, waiting for tenants to “get back on their financial feet and begin to earn a living” before collection could begin.
Rent Recovery Service “never closed an unpaid file.”15 Some of those files contained debt amounts calculated in a reasonable and well-documented way; others contained bloated second and third causes and unreasonably high interest rates.
But since both had the court’s approval, Rent Recovery Service did not distinguish between them.
—
When her turn came, Arleen decided to sit right next to Sherrena at the commissioner’s table.
The two women looked for a moment like old friends or even sisters, with one reflecting life’s favor.
Sherrena was still stewing over being denied her $5,000 claim when the commissioner, without lifting her eyes from Arleen’s file, said, “Your landlady is seeking to evict you for unpaid rent.
```

## 2. `steve_jobs_private_en__17__seed_1`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `Steve Jobs`
- author: `Walter Isaacson`
- chapter: `Chapter Eight: Xerox and Lisa: Graphical User Interfaces` (`17`)
- question_ids: ``
- phenomena: ``
- selection_reason: Illustrates Apple's parallel development strategy in 1979 through three simultaneous projects (Apple III, Lisa, and Raskin's low-cost machine) that would eventually compete for the company's future direction.
- judge_focus: Evaluate whether the model correctly identifies all three Apple projects mentioned in the excerpt and understands they were presented as parallel simultaneous efforts rather than sequential ones. Assess whether the model recognizes the skunkworks project (Raskin's machine) as representing an alternative vision for affordable personal computing.
- latest_review_action: `revise`
- latest_problem_types: `ambiguous_focus|weak_excerpt`
- latest_revised_bucket: `technology_history`
- latest_notes: The core issue is the mismatch between the stated judge focus ('chronological sequence') and the excerpt content which explicitly presents three parallel 'ponies' in fall 1979 with no temporal ordering. Additionally, the selection reason references the Macintosh emergence but the excerpt doesn't show what became of Raskin's project - this disconnect between claimed significance and excerpt content weakens the case. The case needs either a matching judge focus or expanded excerpt showing project outcomes.

```text
Jobs had resisted, thinking that BASIC was all the Apple II needed, but he told Atkinson, “Since you’re so passionate about it, I’ll give you six days to prove me wrong.”
He did, and Jobs respected him ever after.
By the fall of 1979 Apple was breeding three ponies to be potential successors to the Apple II workhorse.
There was the ill-fated Apple III.
There was the Lisa project, which was beginning to disappoint Jobs.
And somewhere off Jobs’s radar screen, at least for the moment, there was a small skunkworks project for a low-cost machine that was being developed by a colorful employee named Jef Raskin, a former professor who had taught Bill Atkinson.
Raskin’s goal was to make an inexpensive “computer for the masses” that would be like an appliance—a self-contained unit with computer, keyboard, monitor, and software all together—and have a graphical interface.
```

## 3. `steve_jobs_private_en__17__seed_2`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `Steve Jobs`
- author: `Walter Isaacson`
- chapter: `Chapter Eight: Xerox and Lisa: Graphical User Interfaces` (`17`)
- question_ids: ``
- phenomena: ``
- selection_reason: Tests understanding of why Xerox failed commercially despite pioneering GUI technology at PARC - illustrating that good ideas alone aren't enough without effective execution, pricing, and market fit.
- judge_focus: Evaluate whether the model correctly identifies that Xerox failed due to poor execution (clunky performance, excessive $16,595 cost, misaligned target market) rather than lack of innovation, and recognizes the business lesson about execution quality being as important as idea quality.
- latest_review_action: `revise`
- latest_problem_types: `wrong_bucket|too_easy`
- latest_revised_bucket: `business_strategy`
- latest_notes: The bucket 'narrative_reflective' is wrong - this excerpt is fundamentally about business strategy (why execution matters as much as innovation). The 'too_easy' concern is valid: the excerpt explicitly states 'good execution is as important as good ideas' and lists three clear failure factors verbatim. However, the case has concrete verifiable details ($16,595, 30k units) that still require causal reasoning to properly evaluate. Should be re-bucketed to business_strategy before benchmark entry.

```text
It’s not as if Xerox executives ignored what their scientists had created at PARC.
In fact they did try to capitalize on it, and in the process they showed why good execution is as important as good ideas.
In 1981, well before the Apple Lisa or Macintosh, they introduced the Xerox Star, a machine that featured their graphical user interface, mouse, bitmapped display, windows, and desktop metaphor.
But it was clunky (it could take minutes to save a large file), costly ($16,595 at retail stores), and aimed mainly at the networked office market.
It flopped; only thirty thousand were ever sold.
Jobs and his team went to a Xerox dealer to look at the Star as soon as it was released.
But he deemed it so worthless that he told his colleagues they couldn’t spend the money to buy one.
```

## 4. `steve_jobs_private_en__24__seed_1`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `Steve Jobs`
- author: `Walter Isaacson`
- chapter: `Chapter Fifteen: The Launch: A Dent in the Universe` (`24`)
- question_ids: ``
- phenomena: ``
- selection_reason: 
- judge_focus: 
- latest_review_action: `revise`
- latest_problem_types: `other`
- latest_revised_bucket: ``
- latest_notes: This is a seed excerpt (status: private_library_seed_v2) explicitly flagged for later curation before benchmark promotion. The missing metadata (case_title, question_ids, judge_focus) is by design, not a case defect. The excerpt itself is coherent biographical content about Jobs and the 1984 Apple ad. Return to curation pipeline to add required evaluation metadata rather than dropping.

```text
A short while later Apple’s Fremont factory began to roll out boxes emblazoned with the colorful line drawings of the Macintosh.
Real artists ship, Jobs had declared, and now the Macintosh team had.
The “1984” Ad
In the spring of 1983, when Jobs had begun to plan for the Macintosh launch, he asked for a commercial that was as revolutionary and astonishing as the product they had created.
“I want something that will stop people in their tracks,” he said.
“I want a thunderclap.”
The task fell to the Chiat/Day advertising agency, which had acquired the Apple account when it bought the advertising side of Regis McKenna’s business.
```

## 5. `steve_jobs_private_en__24__seed_2`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `Steve Jobs`
- author: `Walter Isaacson`
- chapter: `Chapter Fifteen: The Launch: A Dent in the Universe` (`24`)
- question_ids: ``
- phenomena: ``
- selection_reason: 
- judge_focus: 
- latest_review_action: `revise`
- latest_problem_types: `other`
- latest_revised_bucket: ``
- latest_notes: While the excerpt content is coherent and the primary review provided useful framing (strategic flattery/manipulation), the case still lacks essential evaluation metadata (question_ids, phenomena). The adversarial review correctly notes that the alleged wrongdoing (flattery vs. deception) is ambiguous. The case needs proper evaluation questions configured before it can be assessed as a benchmark entry.

```text
Most of all, Jobs fretted about his presentation.
Sculley fancied himself a good writer, so he suggested changes in Jobs’s script.
Jobs recalled being slightly annoyed, but their relationship was still in the phase when he was lathering on flattery and stroking Sculley’s ego.
“I think of you just like Woz and Markkula,” he told Sculley.
“You’re like one of the founders of the company.
They founded the company, but you and I are founding the future.”
Sculley lapped it up.
```

## 6. `supremacy_private_en__13__seed_1`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `Supremacy`
- author: `Parmy Olson`
- chapter: `Chapter 7. Playing Games` (`13`)
- question_ids: ``
- phenomena: ``
- selection_reason: Examines DeepMind's independent governance structure post-2015 spinout, focusing on ethics board composition and transparency mechanisms around high-profile director appointments (Obama, former VP, former CIA director)
- judge_focus: Evaluate the effectiveness and credibility of independent oversight structures in AI labs, particularly whether high-profile external directors provide meaningful governance or primarily serve as legitimacy proxies
- latest_review_action: `revise`
- latest_problem_types: `weak_excerpt|wrong_bucket`
- latest_revised_bucket: `ai_governance_corporate_structure`
- latest_notes: The original 'supremacy' bucket is incorrect—this excerpt discusses corporate governance structures, not AI capability risks. The excerpt is weakened by being entirely prospective ('Decisions would be made', 'would also be') with no evidence of actual outcomes. It describes who was asked to join but not whether they served, what decisions they made, or if the structure functioned. The case needs either outcome-based information about whether this governance model actually worked, or should be dropped if such evidence doesn't exist in the source material.

```text
Decisions would be made by majority vote.
Crucially, there would also be a fully independent board of trustees made up of six directors who would oversee DeepMind’s compliance with its social and ethical mission.
The names of those directors, as well as their decisions, would be made transparent to the public.
Since those six directors would be steering some of the most powerful and potentially dangerous technology in the world, they needed to be high-caliber, trustworthy people.
So DeepMind reached for the stratosphere, asking former president Barack Obama to become one of those directors, along with a former US vice president and a former CIA director.
Several of these people agreed to take part, according to someone who was close to that work.
After consulting with legal experts, DeepMind decided it would not go down the same route that Sam Altman initially had by becoming a nonprofit organization.
```
