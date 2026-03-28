# Revision/Replacement Packet `attentional_v2_private_library_cleanup_en_round_next`

This packet was generated automatically from cases whose current `benchmark_status` requires another hardening round.

## Dataset
- dataset_id: `attentional_v2_private_library_excerpt_en_v2`
- family: `excerpt_cases`
- language_track: `en`
- version: `2`
- targeted_statuses: `needs_revision|needs_replacement|needs_revision`

## Review Actions
- `keep`
- `revise`
- `drop`
- `unclear`

## Confidence
- `high`
- `medium`
- `low`

## 1. `fooled_by_randomness_private_en__14__seed_2`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `Fooled by Randomness`
- author: `Nassim Nicholas Taleb`
- chapter: `Chapter Seven` (`14`)
- question_ids: ``
- phenomena: ``
- selection_reason: Tests ability to resolve anaphoric references and understand philosophical argumentation about verification vs falsification, where 'These people' explicitly refers to logical positivists.
- judge_focus: Can the reader correctly resolve 'These people' to logical positivists/Vienna Circle and understand Popper's falsification approach as opposing verificationism?
- latest_review_action: `revise`
- latest_problem_types: `text_noise|source_parse_problem`
- latest_revised_bucket: `philosophy_of_science_reasoning`
- latest_notes: Two critical issues remain: (1) The chapter_id (14) still mismatches chapter_title (Chapter Seven), indicating unresolved source parsing that needs correction. (2) The lookback_sentences contain contradictory noise ('These are scientists. But they could be anything.') that the primary reviewer correctly identified as undermining test clarity. The excerpt itself is strong and thematically appropriate for Taleb's work, but requires the lookback context to be replaced with supportive material before promotion.

```text
Popper intellectually came to the world with the dramatic shifts in philosophy as attempts were made to shift it from the verbal and rhetorical to the scientific and rigorous, as we saw with the presentation of the Vienna Circle in Chapter 4 .
These people were sometimes called the logical positivists, after the movement called positivism pioneered in France in the nineteenth century by Auguste Comte, where positivism meant scientification of things (literally everything under the sun).
It was the equivalent of bringing the industrial revolution into the soft sciences.
Without dwelling on positivism, I have to note that Popper is the antidote to positivism.
To him, verification is not possible.
Verificationism is more dangerous than anything else.
Taken to the extreme, Popper’s ideas appear naive and primitive—but they work.
```

## 2. `poor_charlies_almanack_private_en__10__seed_1`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `Poor Charlie's Almanack`
- author: `Charles T. Munger`
- chapter: `The Munger Approach to Life, Learning, and Decision Making` (`10`)
- question_ids: ``
- phenomena: ``
- selection_reason: 
- judge_focus: 
- latest_review_action: `revise`
- latest_problem_types: `text_noise|weak_excerpt`
- latest_revised_bucket: ``
- latest_notes: The excerpt content is coherent and discusses accounting limitations with a concrete example (Carl Braun's engineering company). However, critical metadata fields (case_title, question_ids, phenomena, selection_reason, judge_focus) remain empty, preventing proper benchmark evaluation. Additionally, the text parsing artifact where 'C.' and 'E. Braun Engineering Company' are split across lines should be corrected to 'C.E. Braun Engineering Company'. Requires metadata population and text cleaning before re-evaluation.

```text
But you have to know enough about it to understand its limitations-because although accounting is the starting place, it's only a crude approximation.
And it's not very hard to understand its limitations.
For example, everyone can see that you have to more or less just guess at the useful life of a jet airplane or anything like that.
Just because you express the depreciation rate in neat numbers doesn't make it anything you really know.
In terms of the limitations of accounting, one of my favorite stories involves a very great businessman named Carl Braun who created the C.
E Braun Engineering Company.
It designed and built oil refineries-which is very hard to do.
```

## 3. `steve_jobs_private_en__17__seed_1`

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
- latest_problem_types: `too_easy`
- latest_revised_bucket: `technology_history`
- latest_notes: The excerpt is extremely explicit - it directly states 'three ponies' as parallel projects, names all three (Apple III, Lisa, Raskin's skunkworks), and explicitly describes their simultaneity. The text also directly describes Raskin's goal as 'computer for the masses' and 'appliance'-like. This makes it a basic reading comprehension task rather than a meaningful reasoning challenge. While the case addresses the judge focus, it is too easy to be a valuable benchmark case.

```text
Jobs had resisted, thinking that BASIC was all the Apple II needed, but he told Atkinson, “Since you’re so passionate about it, I’ll give you six days to prove me wrong.”
He did, and Jobs respected him ever after.
By the fall of 1979 Apple was breeding three ponies to be potential successors to the Apple II workhorse.
There was the ill-fated Apple III.
There was the Lisa project, which was beginning to disappoint Jobs.
And somewhere off Jobs’s radar screen, at least for the moment, there was a small skunkworks project for a low-cost machine that was being developed by a colorful employee named Jef Raskin, a former professor who had taught Bill Atkinson.
Raskin’s goal was to make an inexpensive “computer for the masses” that would be like an appliance—a self-contained unit with computer, keyboard, monitor, and software all together—and have a graphical interface.
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
- latest_notes: This is a seed excerpt (status: private_library_seed_v2) that explicitly requires curation before benchmark promotion. The missing metadata (case_title, question_ids, judge_focus) is by design, not a defect. The excerpt itself is coherent biographical content about Jobs and the 1984 Apple commercial. Return to curation pipeline to add required evaluation metadata rather than dropping, as the source material has potential.

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
- latest_notes: The excerpt content is coherent and shows a clear example of strategic flattery/manipulation in a business context (Jobs manipulating Sculley through flattery). However, essential evaluation metadata (question_ids, phenomena, selection_reason, judge_focus) is entirely missing, making it impossible to assess bucket fit or evaluation purpose. This case needs proper metadata configuration before it can be judged as a benchmark entry.

```text
Most of all, Jobs fretted about his presentation.
Sculley fancied himself a good writer, so he suggested changes in Jobs’s script.
Jobs recalled being slightly annoyed, but their relationship was still in the phase when he was lathering on flattery and stroking Sculley’s ego.
“I think of you just like Woz and Markkula,” he told Sculley.
“You’re like one of the founders of the company.
They founded the company, but you and I are founding the future.”
Sculley lapped it up.
```

## 6. `evicted_private_en__10__seed_1`

- benchmark_status: `needs_replacement`
- review_status: `llm_reviewed`
- book: `Evicted`
- author: `Matthew Desmond`
- chapter: `Chapter 1: The Business of Owning the City` (`10`)
- question_ids: ``
- phenomena: ``
- selection_reason: 
- judge_focus: 
- latest_review_action: `drop`
- latest_problem_types: `weak_excerpt`
- latest_revised_bucket: ``
- latest_notes: This case lacks all critical metadata (no case_title, question_ids, phenomena, selection_reason, or judge_focus) required for benchmark function. The excerpt is a straightforward relationship origin story with no ethical tension, moral reasoning challenge, or clear evaluation purpose. Even though the primary reviewer proposed potential framing, the current case state cannot function as a benchmark evaluation case and should be dropped.

```text
Sherrena thought he looked like a dope dealer but gave him her real number anyway.
Quentin called Sherrena for three months before she agreed to let him take her out for ice cream.
It took him another six years to marry her.
When Quentin pulled Sherrena over, she was a fourth-grade teacher.
She talked like a teacher, calling strangers “honey” and offering motherly advice or chiding.
“You know I’m fixing to fuss at you,” she would say.
If she sensed your attention starting to drift, she would touch your elbow or thigh to pull you back in.
```

## 7. `evicted_private_en__17__seed_2`

- benchmark_status: `needs_replacement`
- review_status: `llm_reviewed`
- book: `Evicted`
- author: `Matthew Desmond`
- chapter: `Chapter 8: Christmas in Room 400` (`17`)
- question_ids: ``
- phenomena: ``
- selection_reason: 
- judge_focus: 
- latest_review_action: `drop`
- latest_problem_types: `ambiguous_focus|weak_excerpt`
- latest_revised_bucket: ``
- latest_notes: This case has critical structural problems: (1) missing required metadata (selection_reason, judge_focus) making it unusable as benchmark case, (2) the excerpt concatenates two unrelated passages - Rent Recovery Service debt analysis and Arleen's courtroom scene - without coherent focus or judicial task framing. Multiple prior reviews flagged these exact issues. Recommend dropping from active benchmark pipeline.

```text
Like landlords docketing judgments, the company took the long view, waiting for tenants to “get back on their financial feet and begin to earn a living” before collection could begin.
Rent Recovery Service “never closed an unpaid file.”15 Some of those files contained debt amounts calculated in a reasonable and well-documented way; others contained bloated second and third causes and unreasonably high interest rates.
But since both had the court’s approval, Rent Recovery Service did not distinguish between them.
—
When her turn came, Arleen decided to sit right next to Sherrena at the commissioner’s table.
The two women looked for a moment like old friends or even sisters, with one reflecting life’s favor.
Sherrena was still stewing over being denied her $5,000 claim when the commissioner, without lifting her eyes from Arleen’s file, said, “Your landlady is seeking to evict you for unpaid rent.
```

## 8. `poor_charlies_almanack_private_en__10__seed_2`

- benchmark_status: `needs_replacement`
- review_status: `llm_reviewed`
- book: `Poor Charlie's Almanack`
- author: `Charles T. Munger`
- chapter: `The Munger Approach to Life, Learning, and Decision Making` (`10`)
- question_ids: ``
- phenomena: ``
- selection_reason: 
- judge_focus: 
- latest_review_action: `drop`
- latest_problem_types: `weak_excerpt|ambiguous_focus|text_noise|source_parse_problem`
- latest_revised_bucket: ``
- latest_notes: Case has empty critical metadata (selection_reason, judge_focus, question_ids) making it untestable. The excerpt is a vague philosophical complaint about academic psychology with decorative Samuel Johnson anecdote that reads as text noise. No clear evaluation criteria or focus on any specific dangerous idea or misinformation. Fails multiple review dimensions consistently - not worth further curation investment.

```text
And, possibly, the cause of their
inadequacy was the one given by Samuel Johnson in response to a woman who inquired as to what accounted for his dictionary's misdefinition of the word "pastern."
"Pure ignorance," Johnson replied.
And, finally, the text writers showed little
interest in describing standard antidotes to standard
psychology-driven folly, and they thus avoided most
discussion of exactly what most interested me.
```

## 9. `supremacy_private_en__13__seed_1`

- benchmark_status: `needs_replacement`
- review_status: `llm_reviewed`
- book: `Supremacy`
- author: `Parmy Olson`
- chapter: `Chapter 7. Playing Games` (`13`)
- question_ids: ``
- phenomena: ``
- selection_reason: Examines DeepMind's independent governance structure post-2015 spinout, focusing on ethics board composition and transparency mechanisms around high-profile director appointments (Obama, former VP, former CIA director)
- judge_focus: Evaluate the effectiveness and credibility of independent oversight structures in AI labs, particularly whether high-profile external directors provide meaningful governance or primarily serve as legitimacy proxies
- latest_review_action: `drop`
- latest_problem_types: `weak_excerpt`
- latest_revised_bucket: ``
- latest_notes: The excerpt describes DeepMind's intention to recruit high-profile directors but provides no evidence of actual outcomes—whether they served, made decisions, or if the governance structure functioned. The judge focus asks to evaluate effectiveness, but the content offers only prospective plans. This is fundamentally weakened by lacking any outcome data to assess whether this governance model actually worked or was merely performative.

```text
Decisions would be made by majority vote.
Crucially, there would also be a fully independent board of trustees made up of six directors who would oversee DeepMind’s compliance with its social and ethical mission.
The names of those directors, as well as their decisions, would be made transparent to the public.
Since those six directors would be steering some of the most powerful and potentially dangerous technology in the world, they needed to be high-caliber, trustworthy people.
So DeepMind reached for the stratosphere, asking former president Barack Obama to become one of those directors, along with a former US vice president and a former CIA director.
Several of these people agreed to take part, according to someone who was close to that work.
After consulting with legal experts, DeepMind decided it would not go down the same route that Sam Altman initially had by becoming a nonprofit organization.
```
