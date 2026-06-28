from pydantic import BaseModel, Field

from lewisham_server.domain.models import AddressCandidate


class AddressCandidateResponse(BaseModel):
    """A selectable address candidate returned by the address resolver."""

    uprn: str = Field(
        description="Unique Property Reference Number for the address.",
        examples=["100000000001"],
    )
    title: str = Field(
        description="Human-readable address label.",
        examples=["1 Example Street, Catford, SE6 1SQ, London"],
    )

    @classmethod
    def from_domain(cls, address: AddressCandidate) -> "AddressCandidateResponse":
        return cls(uprn=address.uprn, title=address.title)
