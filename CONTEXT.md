# Platform glossary

This file defines concepts only. Normative interfaces, schemas, state machines, and acceptance rules are in [Integration v1](overall/integration-v1.md) and additive [Integration v2](overall/integration-v2.md), [Integration v3](overall/integration-v3.md), [Integration v5](overall/integration-v5.md), and [Integration v6](overall/integration-v6.md); Integration v4 remains an approved/deferred proposal. Frozen pure-value terms remain defined by their module designs.

## Evidence and storage

**Artifact Envelope**

The Domain-owned immutable carrier for a Platform artifact.

_Avoid_: a second Platform envelope, a timestamped envelope

**ArtifactRef**

The Domain-owned typed content coordinate for an Artifact Envelope.

_Avoid_: path, source hash, untyped string ID

**Foundation CAS**

Generic content-addressed storage. Addressable bytes are not evidence until their owner-log publication.

_Avoid_: publication log, Backtest evidence directory

**Owner log**

The domain-designated append-only log in which an artifact becomes published evidence.

_Avoid_: arbitrary caller-selected authority, mutable registry row

**LogEntryRef**

The Foundation coordinate for one verified owner-log entry. It makes publication and conflicting sample/status entries addressable.

_Avoid_: an ArtifactRef, a receipt hash alone

**LogCheckpoint**

A Foundation-assigned immutable prefix of one owner log, fixed by its upper sequence even when later entries share the same governance timestamp.

_Avoid_: caller-chosen future cutoff, proof that no uninstrumented read occurred

**PublicationFactRef**

The coordinate of a governed ref's original Platform-governance fact: a Platform artifact owner-log entry or an integration-owned Backtest evidence-admission entry. Evidence age is anchored here, never at a later status event.

_Avoid_: EvidenceStatusEvent timestamp, refreshed age by delayed registration

**EvidenceStatusEvent / EvidenceStatusSnapshot**

Promotion-owned status provenance and its checkpoint binding. Promotion, not Foundation, interprets status; a publish event binds the subject to its original PublicationFactRef.

_Avoid_: Foundation status enum, cryptographic authorization

**Static historical evidence**

The captured legacy-pilot files and retirement receipt retained for historical cutover evidence.

_Avoid_: callable adapter, canonical Backtest evidence, economic authority

**Backtest publication outcome**

The Backtest public run ref: a nominal `BacktestCanonicalPublicationRef` for completion or a bare Domain `ArtifactRef` for a non-completed run. Repository loading recovers `BLOCKED | FAILED | CANCELLED`; this is not a Research task closure.

_Avoid_: Platform-created terminal, terminal wrapper, zero-return terminal

**BacktestResultGrade**

The single Backtest-owned grade vocabulary used by Research, Validation, and Promotion policy. Accepted Platform flows currently distinguish `development`; the V5 candidate additively activates Backtest-owned `decision_grade` without synthesizing or downgrading grades.

_Avoid_: module-specific grade domains, Platform-computed grade

**BacktestEvidenceAdmission**

The integration-owned proof that an exact Backtest subject was semantically verified before entering Platform governance. Admission@1 owns v1 completion/analysis and the metric profile; Integration v5 adds Admission@2 for exact V2 completion/analysis refs in the same owner log.

_Avoid_: Foundation semantic verification, nominal-ref unwrap, refreshed evidence age

**Backtest target stream**

The v6 Backtest-owned `backtest_target_stream@1` input artifact. Its identity binds a producer-context ref and canonical precomputed target stream; its nominal ref is CAS/exact-read authority, not Platform owner-log evidence. Backtest economic identity uses the verified stream digest rather than the producer context or ref.

_Avoid_: Research evidence, MarketBundle target stream, governed publication, semantic-run producer identity

**Structural target materializer**

The composition-root supplied object whose immutable decision-source `strategy_artifact` and exact `materialize_target(request)` method produce a canonical target result from only the cited immutable MarketBundle.

_Avoid_: loader/plugin registry, network/current-data client, CAS publisher, prepared Backtest request, cache handle

## Research

**RP-THIN-01 compiler TrialDeclaration**

The Frozen source-level declaration emitted by the existing deterministic compiler. It is distinct from `TrialDeclaration@1`; no conversion or reuse is implied.

**TrialDeclaration@1**

The integrated immutable trial coordinate in an Experiment.

_Avoid_: Backtest result, retry attempt

**RP-THIN-01 compiler SelectionPolicy / SelectionPolicy@1**

The Frozen compiler compatibility input and the integrated selection artifact are distinct types despite their shared spelling.

**FeatureRecipe**

The immutable identity of one feature transformation contract: its logical key, code hash, output schema hash, and named inputs. It is a declaration, not executable code or a feature matrix.

_Avoid_: feature callback, plugin, DataFrame

**TrainerRecipe**

The immutable identity of one training contract: its logical key, code hash, model lineage, and explicit hyperparameters. It is not an estimator object, search space, or model loader.

_Avoid_: trainer callback, framework object, hyperparameter search

**ModelBuildPlan**

The pre-result binding of one FeatureRecipe, one TrainerRecipe, one declared training slice, and one seed, content-addressed by a consuming Experiment. It omits Experiment identity to avoid a recursive content-reference cycle; V2 permits at most one plan ref per Experiment.

_Avoid_: mutable training job, tuned result, worker request

**FeatureDatasetManifest**

Research evidence identifying the exact training interval, feature schema, training-data hash, and row count produced for one ModelBuildPlan. It is provenance metadata, not a standardized feature-matrix transport.

_Avoid_: raw feature matrix, proof of complete observation

**ModelBuildEvidence**

The Research owner-log artifact that binds one ModelBuildPlan and FeatureDatasetManifest to the Backtest-owned `ModelArtifactRef` produced by training.

_Avoid_: duplicate ModelArtifactRef, model bytes, deployment artifact

**AnalysisTask / AnalysisTask@1**

In v1/v2 this name denotes the integrated declaration to derive one Backtest analysis for one trial and metric profile; it is not a Frozen pure value or the Backtest analysis result.

_Avoid_: the Backtest analysis result itself

**Task attempt**

Append-only operational evidence for one TaskRef attempt.

_Avoid_: mutable task row, Backtest terminal

**TaskOutcome@1**

The immutable witnessed terminal state of a Research task. It distinguishes completed, Backtest-terminal, upstream, dependency-blocked, and local-failure evidence.

_Avoid_: treating a terminal `ArtifactRef` as a task closure

**ExperimentExecutionManifest**

The exact-cover record of witnessed outcomes for an Experiment at its publication cutoff.

_Avoid_: success-only list, CandidateFamily

**CandidateFamily**

The integrated provenance root that derives Experiment membership and outcomes from an Experiment and its manifest.

_Avoid_: copied trial/outcome set, cross-Experiment family

**StrategyCandidate**

The selected trial, publication, and analysis provenance submitted to Validation. V6 `StrategyCandidate@3` additively selects exact TargetMaterializationEvidence and remains unsupported by Promotion until `TSR-PG-01`.

_Avoid_: validated strategy, deployment authorization

**TargetRecipe**

The v6 Research declaration binding a target key, immutable decision-source strategy artifact, target schema hash, and named inputs. It declares what may be materialized; it is not executable code or a loader.

_Avoid_: callback, module path, mutable parameter search

**TargetBuildTask**

The one-per-Trial Research task with kind/witness `TARGET_BUILD`. The existing integrated `TrialDeclaration@1`, not this task, remains the discovery reservation producer.

_Avoid_: reservation replacement, Backtest run, target CAS artifact

**Target materialization evidence**

Research or Validation owner evidence linking the reserved consumer, recipe, request/input hashes, Backtest target ref/digest, and event count. Its publication is the module replay commit; a target CAS orphan alone is not evidence.

_Avoid_: target payload copy, discovery-as-OOS substitution, economic result

## Validation

**SampleConsumptionRecord**

Validation is the sole semantic owner of `SampleConsumptionRecord`, `SampleConsumptionSnapshot`, and supplied-snapshot projection semantics. In the append-before-read integration it records a logical consumption reservation, not physical I/O completion.

_Avoid_: Foundation event, file access log

**SampleConsumptionSnapshot**

The Frozen in-memory pure projection of supplied consumption records.

_Avoid_: `SampleConsumptionLedgerSnapshot@1`, proof of complete observation

**SampleIntegrityResult**

The Frozen in-memory pure holdout assessment derived from a supplied snapshot.

_Avoid_: `SampleIntegrityAssessment@1`, proof that no uninstrumented read occurred

**SampleConsumptionAppend**

The integration artifact that atomically embeds one canonical record reservation with its producer before that producer reads a market sample. The record is not a separately published artifact.

_Avoid_: mutable consumption status, unpublished record_ref

**SampleConsumptionLedgerSnapshot**

The integration artifact binding Validation to an authoritative Foundation checkpoint.

_Avoid_: the Frozen in-memory snapshot

**SampleIntegrityAssessment**

The integration artifact that addresses conflicts through their Foundation log entries.

_Avoid_: the Frozen pure result

**ValidationPlan**

A pre-result immutable plan for one candidate and its required checks. V6 `ValidationPlan@2` additionally binds the exact target recipe and immutable strategy artifact while preserving every v1 byte.

_Avoid_: result-tuned threshold, recommendation

**ValidationCase / ValidationCaseResult@1**

An integrated immutable check and its immutable observed outcome; neither is a Frozen pure value. Candidate provenance resolves through the Plan.

_Avoid_: shared cached result, duplicate candidate/family identity

**ValidationReport**

Validation’s immutable `supported`, `rejected`, or `inconclusive` conclusion, resolved through its Plan.

_Avoid_: Shadow authorization, mutable status

## Promotion

**PromotionPolicy**

The Promotion-owned rule that evaluates governed evidence. The accepted v1 interface is negative-only; Integration v3 reuses the same policy for additive positive eligibility.

_Avoid_: deployment configuration

**PromotionCase**

The immutable binding of a ValidationReport, policy, and opener. Candidate provenance resolves through the report.

_Avoid_: Shadow proposal, mutable ticket

**PromotionReview**

An independently attested review evaluated with required-role and actor-identity constraints.

_Avoid_: cryptographic authorization

**PromotionEvaluation**

The automatic result at a governed status snapshot and review checkpoint. `PromotionEvaluation@1` is negative-only; `PromotionEvaluation@2` additively admits `ELIGIBLE`.

_Avoid_: deployment authority

**shadow_ready**

The evidence-only `PromotionDecision@2` conclusion that an eligible case may be cited by a future Shadow proposal. It grants no runtime, trading, credential, or deployment authority.

_Avoid_: Shadow authorization, paper-trading session, deployment approval

**PG-SYN-1 PromotionPolicy, PromotionReview, PromotionEvaluation, PromotionDecision / their `@1` artifacts**

The Frozen synthetic source types and same-spelled integrated provenance artifacts are distinct types; neither converts to the other.

## Shadow

**ShadowSpec**

An immutable observe-only proposal that cites an accepted limitation-free `shadow_ready` decision and precommits one bounded future observation window.

_Avoid_: running Shadow session, market-data subscription, capital allocation, Live authorization
