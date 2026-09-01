import pytest

from app.slit_diagnostics import SlitPairDiagnostics
from app.slit_observation_store import save_slit_observation


def test_slit_observation_rejects_wrong_lane_identity():
    a={"id":1,"lane_id":"belt","camera_id":"top","frame_sequence":1,"position_ft":1.0}
    b={"id":2,"lane_id":"belt-b","camera_id":"top","frame_sequence":1,"position_ft":1.0}
    diagnostics=SlitPairDiagnostics(5,20.0,50.0,30.0,60)
    with pytest.raises(ValueError,match="belt-a and belt-b"):
        save_slit_observation(1,a,b,diagnostics)
