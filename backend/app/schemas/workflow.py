from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


class ConversationStatus(str, Enum):
    COLLECTING = "COLLECTING"
    READY = "READY"
    GENERATED = "GENERATED"


class Intent(BaseModel):
    """What the user wants automated, independent of any vendor."""

    model_config = ConfigDict(extra="forbid")

    summary: str | None = None
    tags: list[str] = Field(default_factory=list)


class TriggerSource(BaseModel):
    """Where the trigger originates (inbox, store, webhook, app, etc.)."""

    model_config = ConfigDict(extra="forbid")

    kind: str | None = None
    identifier: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class Trigger(BaseModel):
    """The event or time signal that starts the workflow."""

    model_config = ConfigDict(extra="forbid")

    kind: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class Schedule(BaseModel):
    """Timing for time-based triggers. All fields are user-stated; none are defaulted."""

    model_config = ConfigDict(extra="forbid")

    frequency: str | None = None
    cron: str | None = None
    timezone: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class Condition(BaseModel):
    """A user-stated filter or branch. Optional unless the user introduced one."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: new_id("cond"))
    expression: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class Action(BaseModel):
    """A step to perform. `kind` is an open string so new apps do not require a code change."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: new_id("act"))
    kind: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    needs_recipients: bool = False
    required_parameters: list[str] = Field(default_factory=list)


class Recipient(BaseModel):
    """Delivery target for actions that notify or send."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: new_id("rcpt"))
    channel: str | None = None
    address: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class Preferences(BaseModel):
    """Cross-cutting user preferences. Unknown keys are stored, not dropped."""

    model_config = ConfigDict(extra="allow")

    timezone: str | None = None
    language: str | None = None


class CollectedValue(BaseModel):
    """Ledger entry for a fact the user actually provided."""

    model_config = ConfigDict(extra="forbid")

    path: str
    value: Any
    utterance_id: str | None = None
    updated_at: datetime = Field(default_factory=_utc_now)


class MissingField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    reason: str


class AmbiguityOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str


class Ambiguity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: new_id("amb"))
    path: str
    question: str
    options: list[AmbiguityOption] = Field(default_factory=list)
    resolved: bool = False
    chosen: str | None = None


class FieldUpdate(BaseModel):
    """One dotted-path assignment from a user turn (several may arrive together)."""

    model_config = ConfigDict(extra="forbid")

    path: str
    value: Any


class AmbiguityResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ambiguity_id: str
    chosen: str


class WorkflowStatePatch(BaseModel):
    """
    Structured facts for a single user message.

    Omitted fields mean 'not mentioned'. Nested models use exclude_unset merge
    so one message can set trigger and actions without wiping the other.
    """

    model_config = ConfigDict(extra="forbid")

    intent: Intent | None = None
    trigger: Trigger | None = None
    trigger_source: TriggerSource | None = None
    schedule: Schedule | None = None
    conditions: list[Condition] | None = None
    actions: list[Action] | None = None
    recipients: list[Recipient] | None = None
    preferences: Preferences | None = None
    ambiguities: list[Ambiguity] | None = None
    field_updates: list[FieldUpdate] = Field(default_factory=list)
    resolve_ambiguities: list[AmbiguityResolution] = Field(default_factory=list)
    replace_conditions: bool = False
    replace_actions: bool = False
    replace_recipients: bool = False
    remove_condition_ids: list[str] = Field(default_factory=list)
    remove_action_ids: list[str] = Field(default_factory=list)
    remove_recipient_ids: list[str] = Field(default_factory=list)


class WorkflowState(BaseModel):
    """Canonical conversation/workflow state. Schema evolves via schema_version."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    status: ConversationStatus = ConversationStatus.COLLECTING
    intent: Intent = Field(default_factory=Intent)
    trigger: Trigger = Field(default_factory=Trigger)
    trigger_source: TriggerSource = Field(default_factory=TriggerSource)
    schedule: Schedule | None = None
    conditions: list[Condition] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    recipients: list[Recipient] = Field(default_factory=list)
    preferences: Preferences = Field(default_factory=Preferences)
    collected: dict[str, CollectedValue] = Field(default_factory=dict)
    missing_mandatory_fields: list[MissingField] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)
