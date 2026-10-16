import { useEffect } from "react";
import { Route, Routes, useLocation } from "react-router";
import Header, { BottomNav } from "./components/Header.jsx";
import Footer from "./components/Footer.jsx";
import Discover from "./pages/Discover.jsx";
import EventPage from "./pages/EventPage.jsx";
import Onboarding from "./pages/Onboarding.jsx";
import Season from "./pages/Season.jsx";
import Sports from "./pages/Sports.jsx";
import SportPage from "./pages/SportPage.jsx";
import NotFound from "./pages/NotFound.jsx";

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [pathname]);
  return null;
}

export default function App() {
  return (
    <>
      <ScrollToTop />
      <Header />
      <main className="main">
        <Routes>
          <Route path="/" element={<Discover />} />
          <Route path="/events/:slug" element={<EventPage />} />
          <Route path="/events/:slug/:tab" element={<EventPage />} />
          <Route path="/start" element={<Onboarding />} />
          <Route path="/profile" element={<Onboarding edit />} />
          <Route path="/season" element={<Season />} />
          <Route path="/sports" element={<Sports />} />
          <Route path="/sports/:slug" element={<SportPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
      <BottomNav />
    </>
  );
}
