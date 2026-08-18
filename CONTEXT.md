# Platform glossary

This file defines concepts only. Normative interfaces, schemas, state machines, and acceptance rules are in [Integration v1](overall/integration-v1.md) and additive [Integration v2](overall/integration-v2.md). Frozen pure-value terms remain defined by their module designs.

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

The single Backtest-owned grade vocabulary used by Research, Validation, and Promotion policy.

_Avoid_: module-specific grade domains

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

The pre-result binding of one Experiment, one FeatureRecipe, one TrainerRecipe, one declared training slice, and one seed. V2 permits at most one per Experiment.

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

The selected trial, publication, and analysis provenance submitted to Validation.

_Avoid_: validated strategy, deployment authorization

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

A pre-result immutable plan for one candidate and its required v1 checks.

_Avoid_: result-tuned threshold, recommendation

**ValidationCase / ValidationCaseResult@1**

An integrated immutable check and its immutable observed outcome; neither is a Frozen pure value. Candidate provenance resolves through the Plan.

_Avoid_: shared cached result, duplicate candidate/family identity

**ValidationReport**

Validation’s immutable `supported`, `rejected`, or `inconclusive` conclusion, resolved through its Plan.

_Avoid_: Shadow authorization, mutable status

## Promotion

**PromotionPolicy**

The Promotion-owned rule that evaluates governed evidence on the negative-only path.

_Avoid_: deployment configuration

**PromotionCase**

The immutable binding of a ValidationReport, policy, and opener. Candidate provenance resolves through the report.

_Avoid_: Shadow proposal, mutable ticket

**PromotionReview**

An independently attested review evaluated with required-role and actor-identity constraints.

_Avoid_: cryptographic authorization

**PromotionEvaluation**

The negative-only automatic result at a governed status snapshot and review checkpoint.

_Avoid_: positive eligibility, deployment authority

**PG-SYN-1 PromotionPolicy, PromotionReview, PromotionEvaluation, PromotionDecision / their `@1` artifacts**

The Frozen synthetic source types and same-spelled integrated provenance artifacts are distinct types; neither converts to the other.
