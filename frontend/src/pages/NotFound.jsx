import { Link } from "react-router";
import { EmptyState } from "../components/ui.jsx";

export default function NotFound() {
  return (
    <div className="container page">
      <EmptyState
        title="Off course"
        action={
          <Link to="/" className="btn btn-ink btn-sm">
            Back to the start line
          </Link>
        }
      >
        This page does not exist. The route marshals point you back to Discover.
      </EmptyState>
    </div>
  );
}
