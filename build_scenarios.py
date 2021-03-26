from basic_sim_model import BasicSimulation
from build_packets import build_packets
import pickle
from  pathlib import Path

FOLDER = Path("scenarios")

for scenario in FOLDER.iterdir():
    if scenario.suffix != ".json":
        continue
    sim = BasicSimulation.parse_file(scenario)
    packets = build_packets(sim)
    Path(f"packets/").mkdir(parents=True, exist_ok=True)
    FILE = Path(f"packets/{scenario.stem}.pickle")
    pickle.dump(packets, open(FILE, 'wb'))
    opackets = pickle.load(open(FILE, 'rb'))
    assert packets == opackets



