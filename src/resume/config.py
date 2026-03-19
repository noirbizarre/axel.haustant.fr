from pathlib import Path

from cyclopts import Parameter
from pydantic import BaseModel, Field


@Parameter(name="*")
class Config(BaseModel):
    languages: list[str] = Field(default_factory=list, description="Processed languages")
    root: Path = Field(default_factory=Path, description="Project root directory")

    @property
    def default_language(self) -> str | None:
        return self.languages[0] if self.languages else None


@Parameter(name="*")
class Deploy(BaseModel):
    url: str = Field(default="", description="Deployment URL")
    google_analytics: str | None = Field(default=None, description="Google Analytics Tracking ID")
