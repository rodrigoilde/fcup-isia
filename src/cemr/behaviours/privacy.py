"""Disclosure policy of the PrivacyGuardian (decision D7, rules OS5 and OS11).

Need to know:
- precise location and building access: the case coordinator (a hub) and the EMS unit, while the
  case is active, with the subject's consent or, for P1/P2 with the subject unable to consent, on
  the basis of vital interests (GDPR art. 9(2)(c));
- clinical data and identity: only the EMS unit of the case.
The coordinator forwards the location only inside P09/P10 awards.
"""

from dataclasses import dataclass

from ..protocol.ontology import DisclosureField

VITAL_PRIORITIES = {"P1", "P2"}
LOCATION_FIELDS = {DisclosureField.PRECISE_LOCATION, DisclosureField.BUILDING_ACCESS}
EMS_ONLY_FIELDS = {DisclosureField.CLINICAL, DisclosureField.IDENTITY}


@dataclass(frozen=True)
class DisclosureDecision:
    granted: bool
    reason: str


def decide_disclosure(field_name: str, requester_kind: str, priority: str,
                      case_active: bool = True, consent: bool = False) -> DisclosureDecision:
    if not case_active:
        return DisclosureDecision(False, "case_not_active")
    if field_name in EMS_ONLY_FIELDS:
        if requester_kind != "ems":
            return DisclosureDecision(False, "not_need_to_know")
    elif field_name in LOCATION_FIELDS:
        if requester_kind not in ("hub", "ems"):
            return DisclosureDecision(False, "not_need_to_know")
    else:
        return DisclosureDecision(False, "unknown_field")
    if consent:
        return DisclosureDecision(True, "consent")
    if priority in VITAL_PRIORITIES:
        return DisclosureDecision(True, "vital_interests")
    return DisclosureDecision(False, "no_legal_basis")
