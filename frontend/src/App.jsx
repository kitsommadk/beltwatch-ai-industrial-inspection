import { useEffect, useMemo, useState } from "react";
import { api } from "./api";

const defaults = {
  roll_number: "R-DEMO-07",
  work_order: "WO-18472",
  operator: "Demo Operator",
  run_layout: "single",
  target_width_in: 48,
  belt_a_target_in: 17.5,
  belt_b_target_in: 20,
  tolerance_in: 0.08,
  target_length_ft: 1800,
};

function App() {
  const [form, setForm] = useState(defaults);
  const [session, setSession] = useState(null);
  const [events, setEvents] = useState([]);
  const [summary, setSummary] = useState({ open_events: 0, total_events: 0 });
  const [evidence, setEvidence] = useState([]);
  const [evidenceSummary, setEvidenceSummary] = useState({ total: 0, pass: 0, warning: 0, fail: 0, min_width_in: null, max_width_in: null });
  const [system, setSystem] = useState([]);
  const [runtimeMode, setRuntimeMode] = useState("unknown");
  const [online, setOnline] = useState(false);
  const [selected, setSelected] = useState(null);
  const [notice, setNotice] = useState("Connect the API and start a pilot session");
  const [lastSlitCapture, setLastSlitCapture] = useState(null);

  const running = session?.status === "inspecting";
  const activeLayout = session?.run_layout || form.run_layout;
  const slit = activeLayout === "slit-two-lane";
  const selectedEvent = events.find((event) => event.id === selected) || events[0];
  const completion = session ? Math.min(100, (session.footage_ft / session.target_length_ft) * 100) : 0;
  const tolerance = session?.tolerance_in ?? Number(form.tolerance_in);
  const latestEvidence = evidence[0];
  const latestA = evidence.find((item) => item.lane_id === "belt-a");
  const latestB = evidence.find((item) => item.lane_id === "belt-b");
  const laneTargets = session?.lane_targets || (slit ? { "belt-a": Number(form.belt_a_target_in), "belt-b": Number(form.belt_b_target_in) } : { belt: Number(form.target_width_in) });
  const target = slit ? null : (session?.target_width_in ?? Number(form.target_width_in));

  const chart = useMemo(() => {
    const fallback = [48.01, 48.02, 47.99, 48.03, 48.01, 47.98, 47.96, 47.91, 47.95, 48, 48.02, 47.99, 48.01, 48];
    const singleEvidence = evidence.filter((item) => item.lane_id === "belt" || !item.lane_id);
    const values = singleEvidence.length ? [...singleEvidence].reverse().slice(-14).map((item) => item.measured_width_in) : fallback;
    const center = target || 48;
    const path = values.map((value, index) => `${index ? "L" : "M"} ${index * 44 + 8} ${56 - (value - center) * 420}`).join(" ");
    return { path, values };
  }, [evidence, target]);

  async function refresh() {
    try {
      const [health, nextSession, nextEvents, nextSummary, nextSystem, nextEvidence, nextEvidenceSummary] = await Promise.all([
        api.health(), api.session(), api.events(), api.summary(), api.system(), api.evidence(), api.evidenceSummary(),
      ]);
      setOnline(health.status === "online");
      setRuntimeMode(health.mode || nextSystem.mode || "unknown");
      setSession(nextSession);
      setEvents(nextEvents);
      setSummary(nextSummary);
      setSystem(nextSystem.components);
      setEvidence(nextEvidence);
      setEvidenceSummary(nextEvidenceSummary);
      if (!selected && nextEvents[0]) setSelected(nextEvents[0].id);
    } catch (error) {
      setOnline(false);
      setNotice(error.message);
    }
  }

  useEffect(() => { refresh(); }, []);
  useEffect(() => {
    if (!running) return undefined;
    const timer = window.setInterval(async () => {
      try {
        const next = await api.progress(8);
        setSession(next);
        if (next.status === "complete") setNotice("Target length reached — inspection complete");
      } catch (error) { setNotice(error.message); }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [running]);

  function field(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  function startPayload() {
    if (form.run_layout === "single") {
      const { belt_a_target_in, belt_b_target_in, ...payload } = form;
      return payload;
    }
    const { belt_a_target_in, belt_b_target_in, ...payload } = form;
    const a = Number(belt_a_target_in);
    const b = Number(belt_b_target_in);
    return {
      ...payload,
      target_width_in: a + b,
      lane_targets: { "belt-a": a, "belt-b": b },
    };
  }

  async function startOrPause() {
    try {
      if (!session || session.status === "complete") {
        const next = await api.start(startPayload());
        setSession(next);
        setEvents([]);
        setEvidence([]);
        setLastSlitCapture(null);
        setSelected(null);
        setNotice(`${next.run_layout === "slit-two-lane" ? "Two-lane slit" : "Single-belt"} inspection started — ${runtimeMode} runtime`);
      } else {
        const next = await api.pause();
        setSession(next);
        setNotice(next.status === "paused" ? "Inspection paused — evidence retained" : "Inspection resumed");
      }
      await refresh();
    } catch (error) { setNotice(error.message); }
  }

  async function captureManual(camera, span) {
    try {
      const item = await api.captureEvidence(camera.toLowerCase(), span);
      setNotice(`${camera} evidence BW-E${item.id}: ${item.measured_width_in.toFixed(2)} in · ${item.status}`);
      await refresh();
    } catch (error) { setNotice(error.message); }
  }

  async function captureAuto(camera) {
    try {
      const result = await api.captureAuto(camera.toLowerCase());
      if (result.run_layout === "slit-two-lane") {
        setLastSlitCapture(result);
        const a = result.records.find((record) => record.lane_id === "belt-a");
        const b = result.records.find((record) => record.lane_id === "belt-b");
        setNotice(`${camera} shared frame #${result.shared_frame_sequence}: Belt A ${a.measured_width_in.toFixed(2)} in · Belt B ${b.measured_width_in.toFixed(2)} in`);
      } else {
        setNotice(`${camera} auto evidence BW-E${result.id}: ${result.measured_width_in.toFixed(2)} in · ${result.status}`);
      }
      await refresh();
    } catch (error) { setNotice(error.message); }
  }

  async function detect(kind) {
    try {
      const event = await api.detect(kind);
      setSelected(event.id);
      setNotice(`${event.damage_type} created from the simulated detector`);
      await refresh();
    } catch (error) { setNotice(error.message); }
  }

  async function review(status) {
    if (!selectedEvent) return;
    try {
      await api.review(selectedEvent.id, status, status === "acknowledged" ? "Reviewed by pilot operator" : "Excluded from tuning set");
      setNotice(`BW-${selectedEvent.id} marked ${status.replace("_", " ")}`);
      await refresh();
    } catch (error) { setNotice(error.message); }
  }

  function exportReport() {
    const lines = [
      "BELTWATCH AI — PILOT SESSION REPORT",
      `Runtime: ${runtimeMode}`,
      `Run layout: ${activeLayout}`,
      `Roll: ${session?.roll_number || form.roll_number}`,
      `Work order: ${session?.work_order || form.work_order}`,
      ...(slit
        ? [`Belt A target: ${Number(laneTargets["belt-a"]).toFixed(2)} in`, `Belt B target: ${Number(laneTargets["belt-b"]).toFixed(2)} in`]
        : [`Target: ${Number(target).toFixed(2)} in ± ${Number(tolerance).toFixed(2)} in`]),
      `Target length: ${session?.target_length_ft || form.target_length_ft} ft`,
      `Footage inspected: ${session?.footage_ft || 0} ft`,
      `Evidence: ${evidenceSummary.total} total / ${evidenceSummary.pass} pass / ${evidenceSummary.warning} warning / ${evidenceSummary.fail} fail`,
      "",
      ...evidence.map((item) => `BW-E${item.id} | lane ${item.lane_id || "belt"} | ${item.camera_id} | frame ${item.frame_sequence} | ${item.position_ft} ft | ${item.measured_width_in.toFixed(3)} in | ${item.status} | temporal ${item.temporal_status || "not-assessed"}`),
      "",
      ...events.map((event) => `BW-${event.id} | ${event.damage_type} | ${event.camera} | ${event.location_ft} ft | ${event.status}`),
      "",
      "PORTFOLIO DEMO — SIMULATED/REPLAY PROVIDERS. NO MACHINE CONTROL.",
    ];
    const url = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/plain" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `BeltWatch-${session?.roll_number || "demo"}-report.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main>
      <header>
        <div className="brand"><b>BW</b><span><strong>BeltWatch AI</strong><small>Local Slitter Pilot · Evidence Console</small></span></div>
        <div className="actions"><em>{runtimeMode.toUpperCase()} MODE · {activeLayout.toUpperCase()}</em><i className={online ? "up" : "down"}>● API {online ? "ONLINE" : "OFFLINE"}</i><button onClick={exportReport}>Export report</button></div>
      </header>

      <section className="setup">
        <Input label="Roll number" value={form.roll_number} onChange={(value) => field("roll_number", value)} disabled={running || session?.status === "paused"} />
        <Input label="Work order" value={form.work_order} onChange={(value) => field("work_order", value)} disabled={running || session?.status === "paused"} />
        <Input label="Operator" value={form.operator} onChange={(value) => field("operator", value)} disabled={running || session?.status === "paused"} />
        <Select label="Run layout" value={form.run_layout} onChange={(value) => field("run_layout", value)} disabled={running || session?.status === "paused"} options={[['single','Single belt'],['slit-two-lane','Slit — Belt A + Belt B']]} />
        {form.run_layout === "single" ? (
          <Input label="Target width" type="number" step=".01" value={form.target_width_in} onChange={(value) => field("target_width_in", Number(value))} disabled={running || session?.status === "paused"} />
        ) : <>
          <Input label="Belt A target" type="number" step=".01" value={form.belt_a_target_in} onChange={(value) => field("belt_a_target_in", Number(value))} disabled={running || session?.status === "paused"} />
          <Input label="Belt B target" type="number" step=".01" value={form.belt_b_target_in} onChange={(value) => field("belt_b_target_in", Number(value))} disabled={running || session?.status === "paused"} />
        </>}
        <Input label="Tolerance" type="number" step=".01" value={form.tolerance_in} onChange={(value) => field("tolerance_in", Number(value))} disabled={running || session?.status === "paused"} />
        <Input label="Target length (ft)" type="number" step="25" value={form.target_length_ft} onChange={(value) => field("target_length_ft", Number(value))} disabled={running || session?.status === "paused"} />
        <button className={running ? "pause" : "start"} onClick={startOrPause}>{running ? "Pause inspection" : session?.status === "paused" ? "Resume inspection" : "Start inspection"}</button>
      </section>

      {form.run_layout === "slit-two-lane" && !session && <p className="layout-note">Belt A = left-most lane and Belt B = right-most lane in replay image coordinates. Physical orientation is not yet qualified.</p>}

      <section className="metrics evidence-metrics">
        <Metric label="Session status" value={(session?.status || "ready").toUpperCase()} tone={running ? "good" : "warn"} />
        {slit ? <>
          <Metric label="Belt A width" value={latestA ? `${latestA.measured_width_in.toFixed(2)} in` : `${Number(laneTargets["belt-a"]).toFixed(2)} in target`} tone={latestA?.status === "FAIL" ? "bad" : latestA?.status === "WARNING" ? "warn" : ""} />
          <Metric label="Belt B width" value={latestB ? `${latestB.measured_width_in.toFixed(2)} in` : `${Number(laneTargets["belt-b"]).toFixed(2)} in target`} tone={latestB?.status === "FAIL" ? "bad" : latestB?.status === "WARNING" ? "warn" : ""} />
        </> : <Metric label="Current width" value={`${Number(latestEvidence?.measured_width_in ?? session?.current_width_in ?? target).toFixed(2)} in`} tone={latestEvidence?.status === "FAIL" ? "bad" : latestEvidence?.status === "WARNING" ? "warn" : ""} />}
        <Metric label="Evidence samples" value={evidenceSummary.total} />
        <Metric label="Warnings / fails" value={`${evidenceSummary.warning} / ${evidenceSummary.fail}`} tone={evidenceSummary.fail ? "bad" : evidenceSummary.warning ? "warn" : "good"} />
        <Metric label="Length progress" value={`${Math.round(session?.footage_ft || 0)} / ${session?.target_length_ft || form.target_length_ft} ft`} />
      </section>

      <div className="progress"><span style={{ width: `${completion}%` }} /><b>{completion.toFixed(0)}% of target length</b></div>

      <div className="workspace">
        <div className="primary">
          {slit ? (
            <section className="panel slit-overview">
              <Title title="Two-lane slit measurement" sub="Belt A and Belt B derived independently from one shared frame and one shared position sample" side={lastSlitCapture ? `FRAME #${lastSlitCapture.shared_frame_sequence}` : "AWAITING SHARED FRAME"} />
              <div className="lane-grid">
                <LaneCard name="Belt A" target={laneTargets["belt-a"]} evidence={latestA} />
                <LaneCard name="Belt B" target={laneTargets["belt-b"]} evidence={latestB} />
              </div>
              <div className="diagnostic-grid">
                <Trace label="Gap" value={lastSlitCapture ? `${lastSlitCapture.diagnostics.gap_px} px` : "—"}/>
                <Trace label="A center" value={lastSlitCapture ? `${lastSlitCapture.diagnostics.belt_a_center_x_px.toFixed(1)} px` : "—"}/>
                <Trace label="B center" value={lastSlitCapture ? `${lastSlitCapture.diagnostics.belt_b_center_x_px.toFixed(1)} px` : "—"}/>
                <Trace label="Center distance" value={lastSlitCapture ? `${lastSlitCapture.diagnostics.center_distance_px.toFixed(1)} px` : "—"}/>
                <Trace label="Occupied span" value={lastSlitCapture ? `${lastSlitCapture.diagnostics.total_occupied_span_px} px` : "—"}/>
                <Trace label="Shared position" value={lastSlitCapture ? `${lastSlitCapture.shared_position_ft.toFixed(1)} ft` : "—"}/>
              </div>
              <p className="truth-note">Pair diagnostics are same-frame pixel observations only. They do not assign mechanical root cause.</p>
            </section>
          ) : (
            <section className="panel trend">
              <Title title="Traceable width measurement" sub="Physical width derived from frame geometry and a versioned calibration profile" side={latestEvidence ? `${latestEvidence.status} · ${latestEvidence.position_ft.toFixed(1)} ft` : "AWAITING EVIDENCE"} />
              <div className="chart"><div className="y"><span>+0.10</span><span>target</span><span>-0.10</span></div><svg viewBox="0 0 590 112" preserveAspectRatio="none"><rect x="0" y="16" width="590" height="68"/><line x1="0" x2="590" y1="56" y2="56"/><path d={chart.path}/></svg></div>
              <div className="trace-strip"><Trace label="Camera" value={latestEvidence?.camera_id || "—"}/><Trace label="Frame" value={latestEvidence ? `#${latestEvidence.frame_sequence}` : "—"}/><Trace label="Position" value={latestEvidence ? `${latestEvidence.position_ft.toFixed(1)} ft` : "—"}/><Trace label="Calibration" value={latestEvidence ? `${latestEvidence.calibration_profile_id} · v${latestEvidence.calibration_version}` : "—"}/><Trace label="Temporal" value={latestEvidence?.temporal_status || "—"}/></div>
            </section>
          )}

          <section className="cameras">
            {["Top", "Bottom"].map((camera) => <article className="panel" key={camera}><Title title={`${camera} camera`} sub={camera === "Top" ? "Width + edge geometry" : "Underside surface coverage"} side={running ? "● READY TO CAPTURE" : "● READY"}/><div className={`feed ${camera.toLowerCase()} ${running ? "moving" : ""}`}><div className={`belt ${slit ? "two-lane-belt" : ""}`}><span/><span/><i/>{camera === "Top" && <b/>}</div><small>{runtimeMode.toUpperCase()} FRAME SOURCE · PROVENANCE ENABLED</small></div><div className="capturebar">{slit ? <button onClick={() => captureAuto(camera)}>Capture Belt A + B</button> : <><button onClick={() => captureAuto(camera)}>Auto capture</button><button onClick={() => captureManual(camera, 960)}>Manual nominal</button><button onClick={() => captureManual(camera, 958)}>Manual warning</button></>}</div></article>)}
          </section>

          <section className="panel">
            <Title title="Dimensional evidence ledger" sub="Lane-aware immutable measurement provenance persisted separately from AI/operator events" side={`${evidenceSummary.pass} PASS · ${evidenceSummary.warning} WARN · ${evidenceSummary.fail} FAIL`} />
            <div className="table evidence-table"><div className="row evidence-row headings"><span>Evidence</span><span>Lane / source</span><span>Position</span><span>Width</span><span>Deviation</span><span>Temporal</span><span>Status</span></div>{evidence.length === 0 ? <p className="empty">Start an inspection and capture evidence from either camera.</p> : evidence.slice(0, 30).map((item) => <div className="row evidence-row" key={item.id}><span>BW-E{item.id}<small>{new Date(item.captured_at).toLocaleTimeString()}</small></span><span>{item.lane_id || "belt"}<small>{item.camera_id} · frame #{item.frame_sequence}</small></span><span>{item.position_ft.toFixed(1)} ft<small>{item.position_source}</small></span><span>{item.measured_width_in.toFixed(3)} in<small>{item.measured_span_px.toFixed(1)} px</small></span><span>{item.deviation_in.toFixed(3)} in</span><span>{item.temporal_status || "not assessed"}<small>{item.temporal_width_change_per_ft != null ? `${item.temporal_width_change_per_ft.toFixed(3)} in/ft` : "—"}</small></span><span className={`status ${item.status.toLowerCase()}`}>{item.status}</span></div>)}</div>
          </section>

          <section className="panel">
            <Title title="Inspection events" sub={slit ? "Lane-aware event simulation is intentionally disabled for slit runs" : "AI/detection events remain separate from immutable measurement evidence"} side={!slit && <div className="sim"><button onClick={() => detect("edge")}>Simulate edge defect</button><button onClick={() => detect("width")}>Simulate width deviation</button></div>} />
            <div className="table"><div className="row headings"><span>Event</span><span>Type</span><span>Source</span><span>Position</span><span>Width</span><span>Confidence</span><span>Status</span></div>{events.length === 0 ? <p className="empty">{slit ? "No fabricated lane-aware AI events. This path remains fail-closed until implemented." : "No AI/detection events recorded for this session."}</p> : events.map((event) => <button className={`row ${selectedEvent?.id === event.id ? "selected" : ""}`} onClick={() => setSelected(event.id)} key={event.id}><span>BW-{event.id}<small>{new Date(event.created_at).toLocaleTimeString()}</small></span><span><i className={`sev ${event.severity}`}/>{event.damage_type}</span><span>{event.camera}</span><span>{event.location_ft} ft</span><span>{event.measured_width_in.toFixed(2)} in</span><span>{Math.round(event.confidence * 100)}%</span><span className={`status ${event.status}`}>{event.status.replace("_", " ")}</span></button>)}</div>
          </section>
        </div>

        <aside>
          <section className="panel runtime-card"><Title title="Inspection runtime" sub="Explicit provider configuration" /><div className="runtime-mode"><span>MODE</span><strong>{runtimeMode.toUpperCase()}</strong><small>No silent production fallback</small></div>{system.map((component) => <div className="sys" key={component.name}><b>◇</b><span>{component.name}<small>{component.status}</small></span><i>✓</i></div>)}</section>
          <section className="panel"><Title title="Evidence integrity" sub="Latest dimensional sample" />{latestEvidence ? <dl className="integrity"><Detail label="Evidence ID" value={`BW-E${latestEvidence.id}`}/><Detail label="Lane" value={latestEvidence.lane_id || "belt"}/><Detail label="Payload" value={latestEvidence.payload_ref}/><Detail label="Camera" value={latestEvidence.camera_id}/><Detail label="Frame" value={`#${latestEvidence.frame_sequence}`}/><Detail label="Position source" value={latestEvidence.position_source}/><Detail label="Calibration" value={`v${latestEvidence.calibration_version}`}/><Detail label="Temporal" value={latestEvidence.temporal_status || "not assessed"}/><Detail label="Result" value={latestEvidence.status}/></dl> : <p className="empty">No evidence captured yet.</p>}</section>
          <section className="panel review"><Title title="Event review" sub={selectedEvent ? `BW-${selectedEvent.id}` : "Select an AI event"}/>{selectedEvent && <><div className="evidence"><div><i/></div><small>SIMULATED EVENT EVIDENCE</small></div><dl><Detail label="Condition" value={selectedEvent.damage_type}/><Detail label="Camera" value={selectedEvent.camera}/><Detail label="Location" value={`${selectedEvent.location_ft} ft`}/><Detail label="Measured width" value={`${selectedEvent.measured_width_in.toFixed(2)} in`}/><Detail label="Confidence" value={`${Math.round(selectedEvent.confidence * 100)}%`}/></dl><div className="reviewbuttons"><button onClick={() => review("acknowledged")}>Acknowledge</button><button onClick={() => review("false_positive")}>False positive</button></div></>}</section>
        </aside>
      </div>
      <div className="toast">✓ {notice}</div>
      <footer><b>ASSISTIVE QUALITY CONTROL ONLY</b> No machine control · Operator judgment remains authoritative · Replay/simulation is not physical validation · Calibration thresholds are not production-qualified</footer>
    </main>
  );
}

function Input({ label, ...props }) { return <label>{label}<input {...props} onChange={(event) => props.onChange(event.target.value)} /></label>; }
function Select({ label, options, ...props }) { return <label>{label}<select {...props} onChange={(event) => props.onChange(event.target.value)}>{options.map(([value, text]) => <option value={value} key={value}>{text}</option>)}</select></label>; }
function Metric({ label, value, tone = "" }) { return <div><span>{label}</span><strong className={tone}>{value}</strong></div>; }
function Title({ title, sub, side }) { return <div className="title"><div><h2>{title}</h2><p>{sub}</p></div>{typeof side === "string" ? <em>{side}</em> : side}</div>; }
function Detail({ label, value }) { return <div><dt>{label}</dt><dd>{value}</dd></div>; }
function Trace({ label, value }) { return <div><span>{label}</span><strong>{value}</strong></div>; }
function LaneCard({ name, target, evidence }) { return <div className="lane-card"><span>{name}</span><strong>{evidence ? `${evidence.measured_width_in.toFixed(3)} in` : "Awaiting capture"}</strong><small>Target {Number(target).toFixed(2)} in · {evidence?.status || "NO RESULT"}</small><em>{evidence?.temporal_status || "temporal not established"}</em></div>; }

export default App;
