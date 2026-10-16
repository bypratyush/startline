import { Compass, CalendarCheck, SquaresFour, UserCircle } from "@phosphor-icons/react";
import { Link, NavLink } from "react-router";
import { useAthlete } from "../lib/athlete.jsx";
import Logo from "./Logo.jsx";

function initials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join("");
}

export default function Header() {
  const { athlete } = useAthlete();
  return (
    <header className="header">
      <div className="container header-inner">
        <Logo />
        <nav className="nav" aria-label="Main">
          <NavLink to="/" end>
            Discover
          </NavLink>
          <NavLink to="/sports">Sports</NavLink>
          <NavLink to="/season">My season</NavLink>
        </nav>
        <div className="header-right">
          {athlete ? (
            <Link to="/profile" className="me" title="Edit your profile">
              <span className="me-city">{athlete.city?.name}</span>
              <span className="avatar">{initials(athlete.name)}</span>
            </Link>
          ) : (
            <Link to="/start" className="btn btn-sm btn-ink">
              Build your profile
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}

export function BottomNav() {
  const { athlete } = useAthlete();
  return (
    <nav className="bottom-nav" aria-label="Main">
      <NavLink to="/" end>
        <Compass size={22} />
        <span>Discover</span>
      </NavLink>
      <NavLink to="/sports">
        <SquaresFour size={22} />
        <span>Sports</span>
      </NavLink>
      <NavLink to="/season">
        <CalendarCheck size={22} />
        <span>Season</span>
      </NavLink>
      <NavLink to={athlete ? "/profile" : "/start"}>
        <UserCircle size={22} />
        <span>{athlete ? "Profile" : "Start"}</span>
      </NavLink>
    </nav>
  );
}
