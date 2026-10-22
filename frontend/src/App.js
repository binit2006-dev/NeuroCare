import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Layout from "@/components/Layout";
import Home from "@/pages/Home";
import About from "@/pages/About";
import Downloads from "@/pages/Downloads";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/about" element={<About />} />
          <Route path="/downloads" element={<Downloads />} />
        </Route>
      </Routes>
      <Toaster position="bottom-center" richColors />
    </BrowserRouter>
  );
}

export default App;
