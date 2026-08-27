import { useEffect, useMemo, useState } from "react";
import { api } from "./api";

const defaults = {
  roll_number: "R-DEMO-07",
  work_order: "WO-18472",
  operator: "Demo Operator",
  target_width_in: 48,
  tolerance_in: 0.08,
  target_length_ft: 1800,
};

const readings = [48.01, 48.02, 47.99, 48.03, 48.01, 47.98, 47.96, 47.91, 47.95, 48, 48.02, 47.99, 48.01, 48];

function App() {
  const [form, setForm] = useState(defaults);
  const [session, setSession] = useState(null);
  const [events, setEvents] = useState([]);
  const [summary, setSummary] = useState({ open_events: 0, total_events: 0 });
  const [system, setSystem] = useState([]);
  const [online, setOnline] = useState(false);
  const [selected, setSelected] = useState(null);
  const [notice, setNotice] = useState("Connect the API and start a pilot session");

  const running = session?.status === "inspecting";
  const selectedEvent = events.find((event) => event.id === selected) || events[0];
  const completion = session ? Math.min(100, (session.footage_ft / session.target_length_ft) * 100) : 0;
  const path = useMemo(() => readings.map((value, index) => `${index ? "L" : "M"} ${index * 44 + 8} ${96 - (value - 47.84) * 420}`).join(" "), []);

  async function refresh() {
    try {
      const [health, nextSession, nextEvents, nextSummary, nextSystem] = await Promise.all([
        api.health(), api.session(), api.events(), api.summary(), api.system(),
      ]);
      setOnline(health.status === "online");
      setSession(nextSession);
      setEvents(nextEvents);
      setSummary(nextSummary);
      setSystem(nextSystem.components);
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

  async function startOrPause() {
    try {
      if (!session || session.status === "complete") {
        const next = await api.start(form);
        setSession(next);
        setEvents([]);
        setSelected(null);
        setNotice("Inspection started — simulated measurement stream active");
      } else {
        const next = await api.pause();
        setSession(next);
        setNotice(next.status === "paused" ? "Inspection paused — data retained" : "Inspection resumed");
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
      `Roll: ${session?.roll_number || form.roll_number}`,
      `Work order: ${session?.work_order || form.work_order}`,
      `Target: ${Number(session?.target_width_in || form.target_width_in).toFixed(2)} in ± ${Number(session?.tolerance_in || form.tolerance_in).toFixed(2)} in`,
      `Target length: ${session?.target_length_ft || form.target_length_ft} ft`,
      `Footage inspected: ${session?.footage_ft || 0} ft`,
      "",
      ...events.map((event) => `BW-${event.id} | ${event.damage_type} | ${event.camera} | ${event.location_ft} ft | ${event.status}`),
      "",
      "PORTFOLIO DEMO — SIMULATED DETECTIONS. NO MACHINE CONTROL.",
    ];
    const url = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/plain" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `BeltWatch-${session?.roll_number || "demo"}-report.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  const target = session?.target_width_in ?? Number(form.target_width_in);
  const tolerance = session?.tolerance_in ?? Number(form.tolerance_in);

  return (
    <main>
      <header>
        <div className="brand"><b>BW</b><span><strong>BeltWatch AI</strong><small>Local Slitter Pilot</small></span></div>
        <div className="actions"><em>PORTFOLIO DEMO · SIMULATED DETECTIONS</em><i className={online ? "up" : "down"}>● API {online ? "ONLINE" : "OFFLINE"}</i><button onClick={exportReport}>Export report</button></div>
      </header>

      <section className="setup">
        <Input label="Roll number" value={form.roll_number} onChange={(value) => field("roll_number", value)} />
        <Input label="Work order" value={form.work_order} onChange={(value) => field("work_order", value)} />
        <Input label="Operator" value={form.operator} onChange={(value) => field("operator", value)} />
        <Input label="Target width" type="number" step=".01" value={form.target_width_in} onChange={(value) => field("target_width_in", Number(value))} />
        <Input label="Tolerance" type="number" step=".01" value={form.tolerance_in} onChange={(value) => field("tolerance_in", Number(value))} />
        <Input label="Target length (ft)" type="number" step="25" value={form.target_length_ft} onChange={(value) => field("target_length_ft", Number(value))} />
        <button className={running ? "pause" : "start"} onClick={startOrPause}>{running ? "Pause inspection" : session?.status === "paused" ? "Resume inspection" : "Start inspection"}</button>
      </section>

      <section className="metrics">
        <Metric label="Session status" value={(session?.status || "ready").toUpperCase()} tone={running ? "good" : "warn"} />
        <Metric label="Current width" value={`${Number(session?.current_width_in || target).toFixed(2)} in`} />
        <Metric label="Allowed range" value={`${(target - tolerance).toFixed(2)}–${(target + tolerance).toFixed(2)} in`} />
        <Metric label="Length progress" value={`${Math.round(session?.footage_ft || 0)} / ${session?.target_length_ft || form.target_length_ft} ft`} />
        <Metric label="Open events" value={summary.open_events} tone={summary.open_events ? "warn" : "good"} />
      </section>

      <div className="progress"><span style={{ width: `${completion}%` }} /><b>{completion.toFixed(0)}% of target length</b></div>

      <div className="workspace">
        <div className="primary">
          <section className="panel trend">
            <Title title="Width measurement" sub="Calibrated edge-to-edge measurement across the current roll" />
            <div className="chart"><div className="y"><span>48.10</span><span>48.00</span><span>47.90</span><span>47.80</span></div><svg viewBox="0 0 590 112" preserveAspectRatio="none"><rect x="0" y="16" width="590" height="68"/><line x1="0" x2="590" y1="50" y2="50"/><path d={path}/><circle cx="580" cy="29" r="4"/></svg></div>
          </section>

          <section className="cameras">
            {["Top", "Bottom"].map((camera) => <article className="panel" key={camera}><Title title={`${camera} camera`} sub={camera === "Top" ? "Width + edge geometry" : "Underside surface coverage"} side={running ? "● LIVE" : "● READY"}/><div className={`feed ${camera.toLowerCase()} ${running ? "moving" : ""}`}><div className="belt"><span/><span/><i/>{camera === "Top" && <b/>}</div><small>1920 × 1200　24 FPS　EXP 3.2 ms　GAIN 1.0</small></div></article>)}
          </section>

          <section className="panel">
            <Title title="Inspection events" sub="Evidence and operator disposition persisted by the API" side={<div className="sim"><button onClick={() => detect("edge")}>Simulate edge defect</button><button onClick={() => detect("width")}>Simulate width deviation</button></div>} />
            <div className="table"><div className="row headings"><span>Event</span><span>Type</span><span>Source</span><span>Position</span><span>Width</span><span>Confidence</span><span>Status</span></div>{events.length === 0 ? <p className="empty">Start a session, then create a simulated detection to exercise the workflow.</p> : events.map((event) => <button className={`row ${selectedEvent?.id === event.id ? "selected" : ""}`} onClick={() => setSelected(event.id)} key={event.id}><span>BW-{event.id}<small>{new Date(event.created_at).toLocaleTimeString()}</small></span><span><i className={`sev ${event.severity}`}/>{event.damage_type}</span><span>{event.camera}</span><span>{event.location_ft} ft</span><span>{event.measured_width_in.toFixed(2)} in</span><span>{Math.round(event.confidence * 100)}%</span><span className={`status ${event.status}`}>{event.status.replace("_", " ")}</span></button>)}</div>
          </section>
        </div>

        <aside>
          <section className="panel"><Title title="System status" sub="Local edge inspection stack" />{system.map((component) => <div className="sys" key={component.name}><b>◇</b><span>{component.name}<small>{component.status}</small></span><i>✓</i></div>)}</section>
          <section className="panel review"><Title title="Event review" sub={selectedEvent ? `BW-${selectedEvent.id}` : "Select an event"}/>{selectedEvent && <><div className="evidence"><div><i/></div><small>SIMULATED EVIDENCE FRAME</small></div><dl><Detail label="Condition" value={selectedEvent.damage_type}/><Detail label="Camera" value={selectedEvent.camera}/><Detail label="Location" value={`${selectedEvent.location_ft} ft`}/><Detail label="Measured width" value={`${selectedEvent.measured_width_in.toFixed(2)} in`}/><Detail label="Confidence" value={`${Math.round(selectedEvent.confidence * 100)}%`}/></dl><div className="reviewbuttons"><button onClick={() => review("acknowledged")}>Acknowledge</button><button onClick={() => review("false_positive")}>False positive</button></div></>}</section>
          <section className="panel phases"><Title title="Pilot progression" sub="From controlled validation to production" />{["Installation & imaging", "Baseline capture", "Detection tuning", "Repeatability testing", "Leadership review"].map((label, index) => <div className={`phase ${index < 2 ? "done" : index === 2 ? "active" : ""}`} key={label}><b>{index < 2 ? "✓" : index + 1}</b><span><strong>{label}</strong><small>{index < 2 ? "Prototype complete" : index === 2 ? "Pilot integration" : "Planned"}</small></span></div>)}</section>
        </aside>
      </div>
      <div className="toast">✓ {notice}</div>
      <footer><b>ASSISTIVE QUALITY CONTROL ONLY</b> No machine control · Operator judgment remains authoritative · Synthetic portfolio data</footer>
    </main>
  );
}

function Input({ label, ...props }) { return <label>{label}<input {...props} onChange={(event) => props.onChange(event.target.value)} /></label>; }
function Metric({ label, value, tone = "" }) { return <div><span>{label}</span><strong className={tone}>{value}</strong></div>; }
function Title({ title, sub, side }) { return <div className="title"><div><h2>{title}</h2><p>{sub}</p></div>{typeof side === "string" ? <em>{side}</em> : side}</div>; }
function Detail({ label, value }) { return <div><dt>{label}</dt><dd>{value}</dd></div>; }

export default App;

