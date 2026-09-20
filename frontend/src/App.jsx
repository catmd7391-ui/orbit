import React, { useState, useRef, useEffect } from "react";
import "./App.css";
import { supabase } from "./supabaseClient";
import LoginScreen from "./LoginScreen";

const API_BASE = "http://127.0.0.1:8000";

// ============================================================
// TEMPLATES
// ============================================================

const templates = [
  {
    id: "business",
    name: "Business Report",
    description: "Track business performance, KPIs and important metrics.",
    icon: "📊",
    columns: ["Metric", "January", "February", "March", "Total"],
    rows: [
      ["Revenue", "", "", "", ""],
      ["Expenses", "", "", "", ""],
      ["Profit", "", "", "", ""],
      ["Customers", "", "", "", ""],
    ],
  },
  {
    id: "financial",
    name: "Financial Report",
    description: "Organize income, expenses, profit and financial data.",
    icon: "💰",
    columns: ["Category", "Income", "Expense", "Profit"],
    rows: [
      ["Sales", "", "", ""],
      ["Operations", "", "", ""],
      ["Marketing", "", "", ""],
      ["Other", "", "", ""],
    ],
  },
  {
    id: "project",
    name: "Project Plan",
    description: "Manage tasks, owners, deadlines and project progress.",
    icon: "📋",
    columns: ["Task", "Owner", "Start Date", "End Date", "Status"],
    rows: [
      ["Planning", "", "", "", "Not Started"],
      ["Development", "", "", "", "Not Started"],
      ["Testing", "", "", "", "Not Started"],
      ["Deployment", "", "", "", "Not Started"],
    ],
  },
  {
    id: "sales",
    name: "Sales Tracker",
    description: "Track employees, sales, targets and performance.",
    icon: "📈",
    columns: ["Employee", "January Sales", "Target", "Profit", "Status"],
    rows: [
      ["", "", "", "", ""],
      ["", "", "", "", ""],
      ["", "", "", "", ""],
      ["", "", "", "", ""],
    ],
  },
  {
    id: "employee",
    name: "Employee Details",
    description: "Name, ID, designation, salary and department.",
    icon: "👥",
    columns: ["Name", "Employee ID", "Designation", "Department", "Salary"],
    rows: [
      ["", "", "", "", ""],
      ["", "", "", "", ""],
      ["", "", "", "", ""],
    ],
  },
  {
    id: "student",
    name: "Student Details",
    description: "Name, class, marks, roll number and contact.",
    icon: "📚",
    columns: ["Name", "Class", "Roll No", "Marks", "Contact"],
    rows: [
      ["", "", "", "", ""],
      ["", "", "", "", ""],
      ["", "", "", "", ""],
    ],
  },
  {
    id: "invoice",
    name: "Invoice Template",
    description: "Invoice number, customer, amount, GST and total.",
    icon: "🧾",
    columns: ["Invoice No", "Date", "Customer", "Amount", "GST", "Total"],
    rows: [
      ["", "", "", "", "", ""],
      ["", "", "", "", "", ""],
      ["", "", "", "", "", ""],
    ],
  },
  {
    id: "blank",
    name: "Blank Workbook",
    description: "Start with an empty workbook.",
    icon: "📄",
    columns: ["A", "B", "C", "D"],
    rows: Array.from({ length: 15 }, () => ["", "", "", ""]),
  },
];

const blankTemplate = templates.find((t) => t.id === "blank");

// ============================================================
// HELPERS
// ============================================================

const defaultSteps = [
  { key: "received", label: "Received", status: "idle" },
  { key: "understanding", label: "Understanding", status: "idle" },
  { key: "planning", label: "Planning", status: "idle" },
  { key: "executing", label: "Executing", status: "idle" },
  { key: "verifying", label: "Verifying", status: "idle" },
  { key: "completed", label: "Completed", status: "idle" },
];

function normalizeSteps(serverSteps, status) {
  if (Array.isArray(serverSteps) && serverSteps.length) {
    return serverSteps.map((step, index) => ({
      key: step.key || step.id || `step-${index}`,
      label: step.label || step.name || `Step ${index + 1}`,
      status: step.status || "pending",
      detail: step.detail || step.message || "",
    }));
  }
  if (status === "completed") {
    return defaultSteps.map((s) => ({ ...s, status: "completed" }));
  }
  if (status === "error" || status === "failed") {
    return defaultSteps.map((s, i) => ({
      ...s,
      status: i === 0 ? "completed" : i === 1 ? "error" : "idle",
    }));
  }
  return defaultSteps;
}

function formatTimeAgo(isoString) {
  try {
    const date = new Date(isoString);
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
    if (seconds < 60) return "just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)} days ago`;
    return date.toLocaleDateString();
  } catch {
    return "";
  }
}

// ============================================================
// APP
// ============================================================

function App() {
  // ---------------- AUTH ----------------
  const [session, setSession] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(true);

  // ---------------- NAV ----------------
  const [screen, setScreen] = useState("home");
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [excelStartView, setExcelStartView] = useState("home");

  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [workbook, setWorkbook] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [attachedFile, setAttachedFile] = useState(null);

  const [processing, setProcessing] = useState(false);
  const [activeSheet, setActiveSheet] = useState("Sheet1");
  const [workSteps, setWorkSteps] = useState(defaultSteps);
  const [workStatus, setWorkStatus] = useState("ready");
  const [workMessage, setWorkMessage] = useState("");
  const [documentInfo, setDocumentInfo] = useState(null);
  const [files, setFiles] = useState([]);

  const [pendingPlan, setPendingPlan] = useState(null);

  const [myWorkOpen, setMyWorkOpen] = useState(false);
  const [myWorkItems, setMyWorkItems] = useState(() => {
    try {
      const saved = localStorage.getItem("orbit_my_work");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [searchQuery, setSearchQuery] = useState("");

  const [optionsOpen, setOptionsOpen] = useState(false);
  const [textSize, setTextSize] = useState("medium");
  const [textAlign, setTextAlign] = useState("left");
  const [fullScreen, setFullScreen] = useState(false);

  const messagesEndRef = useRef(null);

  // ============================================================
  // AUTH — load session on mount
  // ============================================================
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session || null);
      setCheckingAuth(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, newSession) => {
        setSession(newSession);
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, processing, pendingPlan]);

  useEffect(() => {
    try {
      localStorage.setItem("orbit_my_work", JSON.stringify(myWorkItems));
    } catch {}
  }, [myWorkItems]);

  // ============================================================
  // AUTO-LOAD the active sheet when workspace opens with no session
  // ============================================================
  useEffect(() => {
    if (screen === "excel-workspace" && workbook && !sessionId) {
      (async () => {
        try {
          const res = await fetch(`${API_BASE}/excel/session`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(workbook),
          });
          if (!res.ok) return;
          const created = await res.json();
          const sid = created.session_id;
          if (!sid) return;
          setSessionId(sid);
          if (created.workbook) setWorkbook({ ...created.workbook });

          const activeSheetName = workbook.sheets?.[0] || "Sheet1";
          const sheetRes = await fetch(
            `${API_BASE}/excel/session/${sid}/sheet/${encodeURIComponent(
              activeSheetName
            )}`
          );
          const data = await sheetRes.json();
          if (data.success) {
            setWorkbook((prev) => ({
              ...(prev || {}),
              columns: data.columns || prev?.columns || ["A", "B", "C", "D"],
              rows: data.rows || [],
              sheets: data.sheets || prev?.sheets || ["Sheet1"],
              active_sheet: activeSheetName,
            }));
            setActiveSheet(activeSheetName);
          }
        } catch (e) {
          console.error("initial sheet load error:", e);
        }
      })();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [screen, workbook?.id]);

  // ============================================================
  // AUTH helpers
  // ============================================================
  const handleLogin = (newSession) => {
    setSession(newSession);
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    setSession(null);
    setWorkbook(null);
    setSessionId(null);
    setMessages([]);
    setScreen("home");
  };

  // ============================================================
  // MY WORK
  // ============================================================

  const saveCurrentToMyWork = () => {
    if (!workbook) return;
    const item = {
      id: `${workbook.id || Date.now()}-${Date.now()}`,
      name: workbook.name || "Workbook.xlsx",
      type: "Excel",
      icon: "📅",
      sheets: workbook.sheets || ["Sheet1"],
      workbook: JSON.parse(JSON.stringify(workbook)),
      sessionId,
      updatedAt: new Date().toISOString(),
    };
    setMyWorkItems((prev) => {
      const withoutSameName = prev.filter((e) => e.name !== item.name);
      return [item, ...withoutSameName];
    });
    setWorkMessage(`Saved ${item.name} to Daily Work.`);
    setWorkStatus("saved");
    setMessages((prev) => [
      ...prev,
      { role: "assistant", text: `💾 Saved "${item.name}" to Daily Work.` },
    ]);
  };

  const openMyWorkItem = (item) => {
    if (item.type === "Excel" && item.workbook) {
      setWorkbook({ ...item.workbook });
      setSelectedTemplate({
        id: "saved",
        name: item.name,
        description: "Saved in Daily Work.",
        icon: "📅",
      });
      setSessionId(item.sessionId || null);
      setActiveSheet(item.workbook.sheets?.[0] || "Sheet1");
      setMessages([]);
      setPendingPlan(null);
      setScreen("excel-workspace");
      setMyWorkOpen(false);
    }
  };

  const deleteMyWorkItem = (id) => {
    setMyWorkItems((prev) => prev.filter((item) => item.id !== id));
  };

  // ============================================================
  // NAV
  // ============================================================

  const login = () => setScreen("terms");
  const acceptTerms = () => {
    if (acceptedTerms) setScreen("home");
  };
  const openExcel = () => {
    setExcelStartView("home");
    setScreen("excel");
  };

  const makeLocalWorkbook = (source) => ({
    id: Date.now(),
    name: source.name,
    templateId: source.id,
    columns: [...(source.columns || ["A", "B", "C", "D"])],
    rows: (source.rows || []).map((row) => [...row]),
    sheets: ["Sheet1"],
  });

  const selectWorkbook = (source) => {
    const localWorkbook = makeLocalWorkbook(source);
    setSelectedTemplate(source);
    setWorkbook(localWorkbook);
    setSessionId(null);
    setMessages([]);
    setWorkSteps(defaultSteps);
    setWorkStatus("ready");
    setWorkMessage("");
    setDocumentInfo(null);
    setFiles([]);
    setInput("");
    setAttachedFile(null);
    setPendingPlan(null);
    setActiveSheet("Sheet1");
    setScreen("excel-chat");
  };

  const createBlankWorkbook = () => selectWorkbook(blankTemplate);

  const handleTemplateClick = (template) => {
    selectWorkbook(template);
  };

  const handleOpenUpload = (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size === 0) {
      alert("The selected file is empty.");
      return;
    }

    const temporaryWorkbook = {
      id: Date.now(),
      name: file.name.replace(/\.[^.]+$/, "") + ".xlsx",
      templateId: "existing",
      columns: ["A", "B", "C"],
      rows: Array.from({ length: 8 }, () => ["", "", ""]),
      sheets: ["Sheet1"],
    };

    setSelectedTemplate({
      id: "existing",
      name: file.name,
      description: "Uploaded file.",
      icon: "📂",
    });
    setWorkbook(temporaryWorkbook);
    setAttachedFile(file);
    setFiles([
      { name: file.name, type: file.type || "Document", size: file.size },
    ]);
    setSessionId(null);
    setMessages([]);
    setWorkSteps(defaultSteps);
    setWorkStatus("ready");
    setWorkMessage("");
    setPendingPlan(null);
    setActiveSheet("Sheet1");
    setScreen("excel-chat");
  };

  // ============================================================
  // SERVER DATA
  // ============================================================

  const applyServerData = (data) => {
    if (data.workbook) setWorkbook({ ...data.workbook });
    if (data.document_analysis || data.document) {
      setDocumentInfo(data.document_analysis || data.document);
    }
    if (Array.isArray(data.files)) setFiles(data.files);
    const actualStatus = data.status || (data.success === false ? "error" : "completed");
    setWorkStatus(actualStatus);
    setWorkMessage(
      data.message ||
        (data.success === false
          ? "Orbit could not complete the requested task."
          : "Orbit completed the requested task.")
    );
    setWorkSteps(normalizeSteps(data.steps, actualStatus));

    if (data.workbook && data.workbook.active_sheet) {
      setActiveSheet(data.workbook.active_sheet);
    }
  };

  const reloadWorkbook = async () => {
    if (!sessionId) return null;
    try {
      const res = await fetch(`${API_BASE}/excel/session/${sessionId}`);
      const data = await res.json();
      if (data.workbook) {
        const stillExists = (data.workbook.sheets || []).includes(activeSheet);
        const targetSheet = stillExists
          ? activeSheet
          : data.workbook.sheets?.[0] || "Sheet1";
        setWorkbook({ ...data.workbook });
        setActiveSheet(targetSheet);
        return data.workbook;
      }
    } catch (e) {
      console.error("reloadWorkbook error:", e);
    }
    return null;
  };

  // ============================================================
  // SWITCH SHEET
  // ============================================================

  const switchSheet = async (sheetName) => {
    setActiveSheet(sheetName);

    let activeSession = sessionId;
    if (!activeSession) {
      try {
        activeSession = await ensureSession();
      } catch (e) {
        console.error("switchSheet ensureSession failed:", e);
        return;
      }
    }

    try {
      const res = await fetch(
        `${API_BASE}/excel/session/${activeSession}/sheet/${encodeURIComponent(
          sheetName
        )}`
      );
      const data = await res.json();

      if (data.success) {
        setWorkbook((prev) => ({
          ...(prev || {}),
          columns: data.columns || prev?.columns || ["A", "B", "C", "D"],
          rows: data.rows || [],
          sheets: data.sheets || prev?.sheets || ["Sheet1"],
          active_sheet: sheetName,
        }));
      } else {
        console.error("switchSheet failed:", data.error);
      }
    } catch (e) {
      console.error("switchSheet error:", e);
    }
  };

  const ensureSession = async () => {
    if (sessionId) return sessionId;
    if (!workbook) throw new Error("No workbook is selected.");
    const response = await fetch(`${API_BASE}/excel/session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(workbook),
    });
    if (!response.ok) throw new Error(`Failed to create session: ${response.status}`);
    const data = await response.json();
    const newSessionId = data.session_id;
    if (!newSessionId) throw new Error("Backend did not return a session ID.");
    setSessionId(newSessionId);
    if (data.workbook) setWorkbook({ ...data.workbook });
    return newSessionId;
  };

  const sendMessage = async () => {
    const cleanInput = input.trim();
    if (!cleanInput && !attachedFile) return;
    if (!workbook) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Please select a workbook first." },
      ]);
      return;
    }

    const currentFile = attachedFile;
    const userText = cleanInput || "Please process the attached file.";

    setMessages((prev) => [
      ...prev,
      { role: "user", text: userText, file: currentFile ? currentFile.name : null },
    ]);

    setInput("");
    setAttachedFile(null);
    setProcessing(true);
    setWorkStatus("working");
    setWorkMessage("Orbit is starting the requested task.");
    setPendingPlan(null);

    if (screen === "excel-chat") setScreen("excel-workspace");

    setWorkSteps(
      defaultSteps.map((step, index) => ({
        ...step,
        status: index === 0 ? "active" : "idle",
      }))
    );

    try {
      const activeSessionId = await ensureSession();
      const formData = new FormData();
      formData.append("message", userText);
      if (currentFile && currentFile.size > 0) formData.append("file", currentFile);

      const response = await fetch(
        `${API_BASE}/excel/session/${activeSessionId}/plan`,
        { method: "POST", body: formData }
      );
      if (!response.ok) throw new Error(`Backend returned ${response.status}`);

      const data = await response.json();
      console.log("Orbit response:", data);

      if (data.already_satisfied) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: data.summary || "Already done." },
        ]);
        setWorkStatus("completed");
      } else if (data.permission_required) {
        setPendingPlan({
          permissionId: data.permission_id,
          summary: data.summary,
          plan: data.plan,
        });
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            text:
              "I prepared a plan:\n\n" +
              data.summary +
              "\n\nApprove to continue.",
          },
        ]);
        setWorkStatus("awaiting_permission");
        setWorkMessage("Waiting for your approval.");
      } else {
        applyServerData(data);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: data.message || "Done." },
        ]);
      }
    } catch (error) {
      console.error(error);
      setWorkStatus("error");
      setWorkMessage(error.message || "Orbit could not process the request.");
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "I couldn't connect to the backend." },
      ]);
    } finally {
      setProcessing(false);
    }
  };

  const approvePlan = async () => {
    if (!pendingPlan) return;
    setProcessing(true);
    try {
      const res = await fetch(
        `${API_BASE}/excel/permission/${pendingPlan.permissionId}/approve`,
        { method: "POST" }
      );
      const data = await res.json();
      applyServerData(data);
      setPendingPlan(null);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: data.message || "Approved and executed." },
      ]);

      if (data.workbook) {
        const sheets = data.workbook.sheets || [];
        const lastSheet = sheets[sheets.length - 1];
        if (lastSheet && lastSheet !== activeSheet) {
          await switchSheet(lastSheet);
        }
      }
    } catch (e) {
      console.error(e);
      setWorkStatus("error");
      setWorkMessage("Approval failed.");
    } finally {
      setProcessing(false);
    }
  };

  const rejectPlan = async () => {
    if (!pendingPlan) return;
    try {
      await fetch(
        `${API_BASE}/excel/permission/${pendingPlan.permissionId}/reject`,
        { method: "POST" }
      );
    } catch (e) {
      console.error(e);
    }
    setPendingPlan(null);
    setWorkStatus("ready");
    setWorkMessage("Plan rejected. Nothing was changed.");
    setMessages((prev) => [
      ...prev,
      { role: "assistant", text: "You rejected the plan. Nothing was changed." },
    ]);
  };

  const downloadWorkbook = async () => {
    let activeSession = sessionId;
    if (!activeSession) {
      try {
        activeSession = await ensureSession();
      } catch (e) {
        alert("Could not start a session. Please try again.");
        return;
      }
    }
    const url = `${API_BASE}/excel/session/${activeSession}/download`;
    const a = document.createElement("a");
    a.href = url;
    a.download = workbook?.name || "Orbit.xlsx";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const saveToCompanyFolder = async () => {
    let activeSession = sessionId;
    if (!activeSession) {
      try {
        activeSession = await ensureSession();
      } catch (e) {
        alert("Could not start a session. Please try again.");
        return;
      }
    }

    const folder = window.prompt(
      "Save to folder (Finance / HR / Projects / Reports / Data):",
      "Finance"
    );
    if (!folder) return;
    const filename = window.prompt("File name:", workbook?.name || "Orbit.xlsx");
    if (!filename) return;

    try {
      const formData = new FormData();
      formData.append("folder", folder);
      formData.append("filename", filename);
      const res = await fetch(
        `${API_BASE}/excel/session/${activeSession}/save-to-folder`,
        { method: "POST", body: formData }
      );
      const data = await res.json();
      if (data.success) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: `✅ Saved to ${folder}/${filename}` },
        ]);
      } else {
        alert("Save failed: " + (data.error || "unknown"));
      }
    } catch (e) {
      console.error(e);
      alert("Save failed.");
    }
  };

  // ============================================================
  // CREATE NEW SHEET
  // ============================================================

  const createNewSheet = async () => {
    let activeSession = sessionId;
    if (!activeSession) {
      try {
        activeSession = await ensureSession();
      } catch (e) {
        console.error(e);
        alert("Could not start a session. Please try again.");
        return;
      }
    }

    const existing = workbook?.sheets || ["Sheet1"];
    const name = window.prompt(
      "Enter new sheet name:",
      `Sheet${existing.length + 1}`
    );
    if (!name) return;

    setProcessing(true);

    try {
      const fd = new FormData();
      fd.append("message", `Create a new sheet called "${name}"`);

      const planRes = await fetch(
        `${API_BASE}/excel/session/${activeSession}/plan`,
        { method: "POST", body: fd }
      );
      const planData = await planRes.json();

      if (planData.permission_required) {
        await fetch(
          `${API_BASE}/excel/permission/${planData.permission_id}/approve`,
          { method: "POST" }
        );
      }

      await reloadWorkbook();
      await switchSheet(name);

      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `✅ Created sheet '${name}'.` },
      ]);
    } catch (e) {
      console.error(e);
      alert("Could not create sheet.");
    } finally {
      setProcessing(false);
    }
  };

  const handleChatFile = (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size === 0) {
      alert("The selected file is empty.");
      return;
    }
    setAttachedFile(file);
    setFiles((prev) => [
      ...prev.filter((item) => item.name !== file.name),
      { name: file.name, type: file.type || "Document", size: file.size },
    ]);
  };

  // ============================================================
  // GO BACK / NEW CHAT
  // ============================================================

  const goBackToExcel = () => {
    setScreen("excel");
    setExcelStartView("home");
    setWorkbook(null);
    setSessionId(null);
    setMessages([]);
    setAttachedFile(null);
    setSelectedTemplate(null);
    setInput("");
    setActiveSheet("Sheet1");
    setWorkSteps(defaultSteps);
    setWorkStatus("ready");
    setWorkMessage("");
    setDocumentInfo(null);
    setFiles([]);
    setMyWorkOpen(false);
    setOptionsOpen(false);
    setPendingPlan(null);
    setFullScreen(false);
    setProcessing(false);
  };

  const startNewChat = () => {
    setScreen("excel");
    setExcelStartView("home");
    setWorkbook(null);
    setSessionId(null);
    setMessages([]);
    setAttachedFile(null);
    setSelectedTemplate(null);
    setInput("");
    setActiveSheet("Sheet1");
    setWorkSteps(defaultSteps);
    setWorkStatus("ready");
    setWorkMessage("");
    setDocumentInfo(null);
    setFiles([]);
    setMyWorkOpen(false);
    setOptionsOpen(false);
    setPendingPlan(null);
    setFullScreen(false);
    setProcessing(false);
  };

  // ============================================================
  // SCREEN: HOME
  // ============================================================

  const renderHome = () => (
    <div className="app-page">
      <header className="top-header">
        <div className="brand-line">
          <div className="brand-mark small">O</div>
          <strong>Orbit</strong>
        </div>
        <div className="header-user">
          <span>{session?.user?.email || "Workspace"}</span>
          <button className="logout-button" onClick={handleLogout}>
            Sign out
          </button>
          <div className="avatar">N</div>
        </div>
      </header>
      <main className="home-content">
        <div className="home-heading">
          <p className="eyebrow">YOUR WORKSPACE</p>
          <h1>What do you want to work on?</h1>
          <p>Choose a workspace and let Orbit handle the software work.</p>
        </div>
        <div className="workspace-grid">
          <button className="workspace-card" onClick={openExcel}>
            <div className="workspace-icon excel-icon">X</div>
            <h2>Excel</h2>
            <p>Build reports, trackers, calculations, dashboards and spreadsheets.</p>
            <span>Open Excel →</span>
          </button>
          <button className="workspace-card" disabled>
            <div className="workspace-icon word-icon">W</div>
            <h2>Word</h2>
            <p>Create reports, documents, proposals and professional writing.</p>
            <span>Coming next</span>
          </button>
          <button className="workspace-card" disabled>
            <div className="workspace-icon powerpoint-icon">P</div>
            <h2>PowerPoint</h2>
            <p>Create presentations, slides, summaries and visual reports.</p>
            <span>Coming next</span>
          </button>
        </div>
      </main>
    </div>
  );

  // ============================================================
  // SCREEN: EXCEL START
  // ============================================================

  const renderExcelStart = () => {
    const userHour = new Date().getHours();
    const greeting =
      userHour < 12 ? "Good morning" : userHour < 18 ? "Good afternoon" : "Good evening";

    const filtered = myWorkItems.filter((item) =>
      item.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
      <div className="excel-start-screen">
        <aside className="excel-start-sidebar">
          <div className="start-brand">
            <div className="brand-mark small">X</div>
            <strong>Excel</strong>
          </div>

          <nav className="start-nav">
            <button
              className={`start-nav-item ${excelStartView === "home" ? "active" : ""}`}
              onClick={() => setExcelStartView("home")}
            >
              <span>🏠</span>
              <span>Home</span>
            </button>

            <button
              className={`start-nav-item ${excelStartView === "new" ? "active" : ""}`}
              onClick={() => setExcelStartView("new")}
            >
              <span>📄</span>
              <span>New</span>
            </button>

            <button
              className={`start-nav-item ${excelStartView === "open" ? "active" : ""}`}
              onClick={() => setExcelStartView("open")}
            >
              <span>📂</span>
              <span>Open</span>
            </button>
          </nav>

          <div className="start-sidebar-bottom">
            <button className="start-nav-item">
              <span>👤</span>
              <span>Account</span>
            </button>
            <button className="start-nav-item">
              <span>⚙️</span>
              <span>Options</span>
            </button>
          </div>
        </aside>

        <main className="excel-start-main">
          {excelStartView === "home" && (
            <>
              <header className="start-header">
                <button className="back-button" onClick={() => setScreen("home")} title="Back">←</button>
                <h1>{greeting}</h1>
                <div className="avatar">N</div>
              </header>

              <section className="start-section">
                <h2>New</h2>
                <div className="start-cards">
                  <button className="start-card" onClick={createBlankWorkbook}>
                    <div className="start-card-icon">📄</div>
                    <div className="start-card-title">Blank workbook</div>
                  </button>
                  <button className="start-card" onClick={() => setExcelStartView("open")}>
                    <div className="start-card-icon">📂</div>
                    <div className="start-card-title">Open existing</div>
                  </button>
                  <button className="start-card" onClick={() => setExcelStartView("new")}>
                    <div className="start-card-icon">📊</div>
                    <div className="start-card-title">See all templates</div>
                  </button>
                  <button className="start-card" onClick={createBlankWorkbook}>
                    <div className="start-card-icon">📈</div>
                    <div className="start-card-title">Formula tutorial</div>
                  </button>
                </div>
              </section>

              <section className="start-section">
                <div className="start-search">
                  <span>🔍</span>
                  <input
                    type="text"
                    placeholder="Search for a file"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
              </section>

              <section className="start-section">
                <div className="daily-work-title-row">
                  <h2>📅 Daily Work</h2>
                  <span className="daily-work-subtitle">
                    Your recurring workbooks. Orbit keeps them updated as you upload.
                  </span>
                </div>

                <div className="start-recent-list">
                  {filtered.length === 0 ? (
                    <div className="start-empty">
                      <p>No daily work yet.</p>
                      <p>
                        Create a <strong>Blank workbook</strong> or{" "}
                        <strong>upload your existing Excel</strong> to get started.
                      </p>
                    </div>
                  ) : (
                    filtered.map((item) => (
                      <button
                        key={item.id}
                        className="start-recent-item daily-work-item"
                        onClick={() => openMyWorkItem(item)}
                      >
                        <div className="start-recent-icon">📅</div>
                        <div className="start-recent-details">
                          <strong>{item.name}</strong>
                          <span className="daily-work-meta">
                            {item.sheets?.length || 1} sheet(s) ·{" "}
                            {item.updatedAt
                              ? `last used ${formatTimeAgo(item.updatedAt)}`
                              : "new"}
                          </span>
                        </div>
                        <span className="daily-work-badge">Daily</span>
                      </button>
                    ))
                  )}
                </div>
              </section>
            </>
          )}

          {excelStartView === "new" && (
            <>
              <header className="start-header">
                <button className="back-button" onClick={() => setExcelStartView("home")}>←</button>
                <h1>New</h1>
                <div className="avatar">N</div>
              </header>

              <section className="start-section">
                <h2>Templates</h2>
                <div className="template-grid">
                  {templates.map((template) => (
                    <button
                      key={template.id}
                      className="template-card"
                      onClick={() => handleTemplateClick(template)}
                    >
                      <div className="template-icon">{template.icon}</div>
                      <h3>{template.name}</h3>
                      <p>{template.description}</p>
                      <span className="template-open">Use template →</span>
                    </button>
                  ))}
                </div>
              </section>
            </>
          )}

          {excelStartView === "open" && (
            <>
              <header className="start-header">
                <button className="back-button" onClick={() => setExcelStartView("home")}>←</button>
                <h1>Open</h1>
                <div className="avatar">N</div>
              </header>

              <section className="start-section">
                <label className="start-upload">
                  <div className="start-upload-icon">📂</div>
                  <div className="start-upload-title">Click to upload a file</div>
                  <div className="start-upload-hint">PDF · XLSX · XLS · CSV · DOCX · PNG · JPG</div>
                  <div className="start-upload-button">Choose file</div>
                  <input
                    type="file"
                    accept=".pdf,.xlsx,.xls,.csv,.docx,.doc,.txt,.png,.jpg,.jpeg"
                    onChange={handleOpenUpload}
                  />
                </label>
              </section>

              <section className="start-section">
                <div className="daily-work-title-row">
                  <h2>📅 Daily Work</h2>
                  <span className="daily-work-subtitle">
                    Your recurring workbooks. Orbit keeps them updated as you upload.
                  </span>
                </div>

                <div className="start-recent-list">
                  {filtered.length === 0 ? (
                    <div className="start-empty">
                      <p>No daily work yet.</p>
                    </div>
                  ) : (
                    filtered.map((item) => (
                      <button
                        key={item.id}
                        className="start-recent-item daily-work-item"
                        onClick={() => openMyWorkItem(item)}
                      >
                        <div className="start-recent-icon">📅</div>
                        <div className="start-recent-details">
                          <strong>{item.name}</strong>
                          <span className="daily-work-meta">
                            {item.sheets?.length || 1} sheet(s) ·{" "}
                            {item.updatedAt
                              ? `last used ${formatTimeAgo(item.updatedAt)}`
                              : "new"}
                          </span>
                        </div>
                        <span className="daily-work-badge">Daily</span>
                      </button>
                    ))
                  )}
                </div>
              </section>
            </>
          )}
        </main>
      </div>
    );
  };

  // ============================================================
  // SCREEN: CHAT
  // ============================================================

  const renderExcelChat = () => (
    <div className="simple-chat-screen">
      <header className="simple-chat-header">
        <div className="brand-line">
          <button className="back-button" onClick={goBackToExcel}>←</button>
          <div className="brand-mark small">O</div>
          <strong>Orbit</strong>
          <span className="header-divider">/</span>
          <span>Excel</span>
        </div>
        <div className="workspace-actions">
          <button type="button" onClick={startNewChat}>＋ New chat</button>
          <div className="avatar">N</div>
        </div>
      </header>
      <main className="simple-chat-main">
        <div className="simple-chat-box">
          <div className="simple-workbook">
            <span className="simple-workbook-icon">📊</span>
            <div>
              <strong>{workbook?.name || "Workbook"}</strong>
              <span>{selectedTemplate?.description || "Ready for your instruction."}</span>
            </div>
          </div>
          {attachedFile && (
            <div className="simple-file-chip">
              <span>📎</span>
              <span>{attachedFile.name}</span>
              <button onClick={() => setAttachedFile(null)}>×</button>
            </div>
          )}
          <textarea
            className="simple-prompt"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            placeholder="What do you want Orbit to do?"
          />
          <div className="simple-actions">
            <label className="simple-attach" title="Attach a file">
              📎
              <input type="file" accept=".pdf,.xlsx,.xls,.csv,.txt,.doc,.docx,.ppt,.pptx,.png,.jpg,.jpeg" onChange={handleChatFile} />
            </label>
            <button className="simple-send" onClick={sendMessage} disabled={!input.trim() && !attachedFile}>
              Send <span>↑</span>
            </button>
          </div>
        </div>
      </main>
    </div>
  );

  // ============================================================
  // MESSAGES + INPUT
  // ============================================================

  const renderMessages = () => (
    <div className="chatbot-messages">
      {messages.length === 0 && (
        <div className="chatbot-welcome">
          <div className="agent-avatar large">O</div>
          <h2>What should I do?</h2>
          <p>Attach a document, describe the work, and press Send.</p>
        </div>
      )}
      {messages.map((message, index) => (
        <div key={index} className={`chatbot-row ${message.role === "user" ? "user-row" : ""}`}>
          {message.role === "assistant" && <div className="message-avatar">O</div>}
          <div className={`chatbot-bubble ${message.role === "user" ? "user-bubble" : "assistant-bubble"}`}>
            <div>{message.text}</div>
            {message.file && <div className="attached-file-message">📎 {message.file}</div>}
          </div>
          {message.role === "user" && <div className="message-avatar user-avatar">N</div>}
        </div>
      ))}
      {pendingPlan && (
        <div className="permission-card-ui">
          <div className="permission-header">🔒 Approval Required</div>
          <p>Orbit wants to make these changes:</p>
          <pre className="permission-summary">{pendingPlan.summary}</pre>
          <div className="permission-actions">
            <button className="approve-btn" onClick={approvePlan}>✅ Approve</button>
            <button className="reject-btn" onClick={rejectPlan}>❌ Reject</button>
          </div>
        </div>
      )}
      {processing && (
        <div className="chatbot-row">
          <div className="message-avatar">O</div>
          <div className="assistant-bubble processing-message">
            <span /><span /><span />
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  );

  const renderInputBar = () => (
    <div className="chatbot-input-area">
      {attachedFile && (
        <div className="selected-file">
          <span>📎</span>
          <span>{attachedFile.name}</span>
          <button onClick={() => setAttachedFile(null)}>×</button>
        </div>
      )}
      <div className="chatbot-input-box">
        <label className="chatbot-attach">
          📎
          <input type="file" accept=".pdf,.xlsx,.xls,.csv,.txt,.doc,.docx,.ppt,.pptx,.png,.jpg,.jpeg" onChange={handleChatFile} disabled={processing} />
        </label>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendMessage();
            }
          }}
          placeholder="Tell Orbit what you want to do..."
          disabled={processing}
          rows={1}
        />
        <button className="chatbot-send" onClick={sendMessage} disabled={processing || (!input.trim() && !attachedFile)} title="Send">↑</button>
      </div>
    </div>
  );

  // ============================================================
  // SPREADSHEET
  // ============================================================

  const renderSpreadsheet = () => {
    if (!workbook) return null;
    const sizeClass = `text-${textSize}`;
    const alignClass = `align-${textAlign}`;
    const columns = workbook.columns || ["A", "B", "C", "D"];
    const rows = workbook.rows || [];
    const sheets = workbook.sheets || ["Sheet1"];

    return (
      <div className="spreadsheet-panel">
        <div className="workbook-toolbar">
          <div className="workbook-title">
            <span className="excel-mini-icon">X</span>
            <div>
              <strong>{workbook.name}</strong>
            </div>
          </div>
        </div>

        <div className="sheet-area">
          <table className={`spreadsheet ${sizeClass} ${alignClass}`}>
            <thead>
              <tr>
                <th className="row-number-header"></th>
                {columns.map((column, index) => (
                  <th key={index}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td className="row-number">1</td>
                  {columns.map((_, columnIndex) => (
                    <td key={columnIndex} className="read-only-cell"></td>
                  ))}
                </tr>
              ) : (
                rows.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    <td className="row-number">{rowIndex + 1}</td>
                    {columns.map((_, columnIndex) => (
                      <td key={columnIndex} className="read-only-cell">
                        {row[columnIndex] ?? ""}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="sheet-tabs">
          {sheets.map((sheet) => (
            <button
              key={sheet}
              className={activeSheet === sheet ? "active-sheet" : ""}
              onClick={() => switchSheet(sheet)}
            >
              {sheet}
            </button>
          ))}
          <button className="add-sheet-button" onClick={createNewSheet} title="Add new sheet">＋</button>
        </div>

        <div className="status-bar">
          <span>{processing ? "Orbit is working..." : "Ready"}</span>
          <span>{rows.length} rows</span>
          <span>{columns.length} columns</span>
          <span>Sheet: {activeSheet}</span>
        </div>
      </div>
    );
  };

  // ============================================================
  // MY WORK DRAWER
  // ============================================================

  const renderMyWork = () => {
    if (!myWorkOpen) return null;
    return (
      <div className="my-work-overlay" onClick={() => setMyWorkOpen(false)}>
        <aside className="my-work-drawer" onClick={(e) => e.stopPropagation()}>
          <div className="my-work-header">
            <div>
              <p className="eyebrow">YOUR WORK</p>
              <h2>Daily Work</h2>
            </div>
            <button className="my-work-close" onClick={() => setMyWorkOpen(false)}>×</button>
          </div>

          <div className="my-work-search">
            <span>⌕</span>
            <input placeholder="Search your work" />
          </div>

          <div className="my-work-actions-row">
            <button type="button" onClick={saveCurrentToMyWork}>＋ Save current</button>
            <button type="button" onClick={() => setMyWorkItems([])}>Clear</button>
          </div>

          <div className="my-work-section-title">RECENT WORK</div>

          <div className="my-work-list">
            {myWorkItems.length === 0 ? (
              <div className="my-work-empty">
                <div className="my-work-empty-icon">📁</div>
                <strong>Your saved work appears here</strong>
                <span>Save a workbook and it will stay in Daily Work.</span>
              </div>
            ) : (
              myWorkItems.map((item) => (
                <div className="my-work-item" key={item.id}>
                  <button className="my-work-item-main" type="button" onClick={() => openMyWorkItem(item)}>
                    <span className="my-work-file-icon">{item.icon || "📄"}</span>
                    <span className="my-work-file-details">
                      <strong>{item.name}</strong>
                      <small>{item.type} · {item.sheets?.length || 1} sheet(s)</small>
                    </span>
                  </button>
                  <button className="item-more-button" onClick={() => deleteMyWorkItem(item.id)} title="Delete">×</button>
                </div>
              ))
            )}
          </div>
        </aside>
      </div>
    );
  };

  // ============================================================
  // SCREEN: WORKSPACE
  // ============================================================

  const renderExcelWorkspace = () => (
    <div className={`excel-workspace live-workspace ${fullScreen ? "full-screen" : ""}`}>
      <header className="workspace-header">
        <div className="brand-line">
          <button className="back-button" onClick={goBackToExcel}>←</button>
          <div className="brand-mark small">O</div>
          <strong>Orbit</strong>
          <span className="header-divider">/</span>
          <span>Excel</span>
        </div>

        <div className="workspace-actions">
          <button type="button" onClick={startNewChat}>＋ New chat</button>
          <button type="button" onClick={() => setMyWorkOpen(true)}>Daily Work</button>
          <button type="button" onClick={saveCurrentToMyWork}>Save</button>
          <button type="button" onClick={downloadWorkbook}>⬇ Download</button>
          <button type="button" onClick={saveToCompanyFolder}>📁 Save to folder</button>
          <button className="workspace-more-button" type="button" title="Options" onClick={() => setOptionsOpen((v) => !v)}>⋮</button>
          <div className="avatar">N</div>
        </div>
      </header>

      <div className={`workspace-body full-width ${fullScreen ? "hide-chat" : ""}`}>
        {!fullScreen && (
          <div className="chat-panel">
            <div className="chat-header">
              <div className="orbit-agent">
                <div className="agent-avatar">O</div>
                <div>
                  <strong>Orbit</strong>
                  <span>Excel agent</span>
                </div>
              </div>
              <div className="agent-status">
                <span className={`status-dot ${processing ? "working-dot" : ""}`} />
                {processing ? "Working" : "Ready"}
              </div>
            </div>
            {renderMessages()}
            {renderInputBar()}
          </div>
        )}

        <main className="workspace-right">
          <div className="right-topbar">
            <div>
              <span className="right-kicker">WORKSPACE</span>
              <strong>{selectedTemplate?.name || workbook?.name || "Workbook"}</strong>
            </div>
            <div className="right-topbar-actions">
              <span className="work-status-text">{processing ? "Orbit is working…" : workStatus}</span>
              {fullScreen && (
                <button className="exit-fullscreen-btn" onClick={() => setFullScreen(false)}>✕ Exit full screen</button>
              )}
            </div>
          </div>

          {documentInfo && documentInfo.fields && Object.keys(documentInfo.fields).length > 0 && (
            <div className="document-analysis-panel">
              <div className="doc-header">
                <span className="doc-type-badge">{documentInfo.document_type || "Document"}</span>
                <span className="doc-confidence">{Math.round((documentInfo.confidence || 0) * 100)}% confidence</span>
              </div>
              <table className="doc-fields-table">
                <thead>
                  <tr><th>Field</th><th>Value</th></tr>
                </thead>
                <tbody>
                  {Object.entries(documentInfo.fields).map(([key, value]) => (
                    <tr key={key}>
                      <td className="doc-field-name">{key}</td>
                      <td className="doc-field-value">{String(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="right-content workbook-only-content">
            {renderSpreadsheet()}
          </div>
        </main>

        {optionsOpen && (
          <div className="options-overlay" onClick={() => setOptionsOpen(false)}>
            <aside className="options-drawer" onClick={(e) => e.stopPropagation()}>
              <div className="options-header">
                <strong>Display options</strong>
                <button onClick={() => setOptionsOpen(false)}>×</button>
              </div>

              <div className="options-group">
                <span className="options-label">Layout</span>
                <div className="options-row">
                  <button className={!fullScreen ? "active" : ""} onClick={() => setFullScreen(false)}>Split</button>
                  <button className={fullScreen ? "active" : ""} onClick={() => setFullScreen(true)}>⛶ Full</button>
                </div>
              </div>

              <div className="options-group">
                <span className="options-label">Text size</span>
                <div className="options-row">
                  <button className={textSize === "small" ? "active" : ""} onClick={() => setTextSize("small")}>S</button>
                  <button className={textSize === "medium" ? "active" : ""} onClick={() => setTextSize("medium")}>M</button>
                  <button className={textSize === "large" ? "active" : ""} onClick={() => setTextSize("large")}>L</button>
                </div>
              </div>

              <div className="options-group">
                <span className="options-label">Align</span>
                <div className="options-row">
                  <button className={textAlign === "left" ? "active" : ""} onClick={() => setTextAlign("left")}>⬅</button>
                  <button className={textAlign === "center" ? "active" : ""} onClick={() => setTextAlign("center")}>↔</button>
                  <button className={textAlign === "right" ? "active" : ""} onClick={() => setTextAlign("right")}>➡</button>
                </div>
              </div>
            </aside>
          </div>
        )}
      </div>

      {renderMyWork()}
    </div>
  );

  // ============================================================
  // ROUTER (with auth gate)
  // ============================================================

  if (checkingAuth) {
    return (
      <div className="login-page">
        <div style={{ color: "#217346", fontSize: 18 }}>Loading…</div>
      </div>
    );
  }

  if (!session) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  if (screen === "home") return renderHome();
  if (screen === "excel") return renderExcelStart();
  if (screen === "excel-chat") return renderExcelChat();
  if (screen === "excel-workspace") return renderExcelWorkspace();
  return renderHome();
}

export default App;