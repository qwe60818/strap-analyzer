
import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Intel Strap Analyzer", layout="wide")
st.title("Intel Strap Analyzer (Web Version)")

# ========== 資料處理函式 ==========
def flip_pin(pin):
    match = re.match(r"(R\d+)\((\d):(\w+)\)", pin)
    if match:
        resistor = match.group(1)
        first = match.group(2)
        flipped = "2" if first == "1" else "1"
        return f"{resistor}({flipped}:x)"
    return pin

def voltage_equivalent(v1, v2):
    def normalize(v):
        return v.replace("+", "").replace("V", "").replace(".", "").replace("P", "").upper()
    return normalize(v1) == normalize(v2)

# ========== 上傳資料 ==========
strap_file = st.file_uploader("Upload Strap CSV File", type=["csv"])
iscf_file = st.file_uploader("Upload ISCF File", type=["txt", "iscf"])

if strap_file and iscf_file:
    strap_df = pd.read_csv(strap_file)
    st.subheader("Strap Data")
    st.dataframe(strap_df)

    # Parse ISCF file content
    content = iscf_file.read().decode("utf-8", errors="replace").splitlines()
    nets = {}
    power = {}
    ground = {}
    section = None

    for line in content:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line == "BEGIN_NETS":
            section = nets
        elif line == "BEGIN_POWER":
            section = power
        elif line == "BEGIN_GROUND":
            section = ground
        elif line.startswith("END_"):
            section = None
        elif section is not None and ":" in line:
            k, v = line.split(":", 1)
            section[k.strip()] = v.strip()

    st.subheader("Compare Results")
    results = []
    for _, row in strap_df.iterrows():
        strap_name = row["Strap name"]
        target_voltage = row["Target voltage"]
        resistor = row["Resistor"]
        note = row["Note"] if "Note" in row else ""
        is_gnd = target_voltage.upper() == "GND"

        # 搜尋匹配的 pin
        matched_nets = []
        net_name = "N/A"
        for k, v in nets.items():
            matches = re.findall(r"\(([^)]+)\)", v)
            for m in matches:
                if m.split("/")[0].strip() == strap_name:
                    matched_nets.append((k, v))
                    net_name = k
                    break

        resistor_pins = []
        for _, v in matched_nets:
            resistor_pins += re.findall(r"(R\d+\(\d:\w+\))", v)
        flipped_pins = [flip_pin(p) for p in resistor_pins]

        found_voltage = "N/A"
        result = "FAIL"
        if is_gnd:
            for pin in flipped_pins:
                for content in ground.values():
                    if any(pin in p for p in re.findall(r"(R\d+\(\d:\w+\))", content)):
                        found_voltage = "GND"
                        result = "PASS"
                        break
        else:
            for pin in flipped_pins:
                for volt, content in {**power, **nets}.items():
                    if any(pin in p for p in re.findall(r"(R\d+\(\d:\w+\))", content)):
                        if voltage_equivalent(volt, target_voltage):
                            found_voltage = volt
                            result = "PASS"
                            break
                if result == "PASS":
                    break

        results.append({
            "Strap name": strap_name,
            "Net name": net_name,
            "Actual V.": found_voltage,
            "Target V.": target_voltage,
            "Resistor": resistor,
            "Result": result,
            "Note": note
        })

    st.dataframe(pd.DataFrame(results))
