import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import DriftHome from "./routes/DriftHome";
import TraceDetail from "./routes/TraceDetail";
import RunComparison from "./routes/RunComparison";
import DriftDetail from "./routes/DriftDetail";
import EvalResults from "./routes/EvalResults";
import Datasets from "./routes/Datasets";
import RunList from "./routes/RunList";
const navItem = "px-3 py-2 hover:underline";
export default function App() {
    return (_jsxs("div", { children: [_jsx("header", { className: "border-b", children: _jsxs("nav", { className: "flex gap-1 px-4 py-2 items-center", children: [_jsx(Link, { to: "/", className: "font-bold mr-4", children: "AgentAid" }), _jsx(NavLink, { to: "/", className: navItem, end: true, children: "Monitoring" }), _jsx(NavLink, { to: "/runs", className: navItem, children: "Traces" }), _jsx(NavLink, { to: "/evals", className: navItem, children: "Evals" }), _jsx(NavLink, { to: "/datasets", className: navItem, children: "Datasets" })] }) }), _jsx("main", { className: "p-6", children: _jsxs(Routes, { children: [_jsx(Route, { path: "/", element: _jsx(DriftHome, {}) }), _jsx(Route, { path: "/runs", element: _jsx(RunList, {}) }), _jsx(Route, { path: "/runs/:id", element: _jsx(TraceDetail, {}) }), _jsx(Route, { path: "/compare", element: _jsx(RunComparison, {}) }), _jsx(Route, { path: "/drift/:signal", element: _jsx(DriftDetail, {}) }), _jsx(Route, { path: "/evals", element: _jsx(EvalResults, {}) }), _jsx(Route, { path: "/datasets", element: _jsx(Datasets, {}) })] }) })] }));
}
