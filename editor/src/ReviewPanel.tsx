import { useEffect, useState } from "react";
import { toast } from "sonner";
import { loadReview, openPreview, publishProgramme, publishStatus, type PublishResult, type ReviewReport } from "./api";

export function ReviewPanel() {
  const [review, setReview] = useState<ReviewReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [published, setPublished] = useState<PublishResult | null>(null);
  const [checks, setChecks] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    loadReview()
      .then((report) => {
        if (!cancelled) {
          setReview(report);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          toast.error(error instanceof Error ? error.message : "Could not review the draft");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function refreshStatus(url: string) {
    const report = await publishStatus(url);
    const lines = report.checks.map((check) => `${check.name}: ${check.status}`);
    setChecks([`Pull request ${report.state}`, ...lines, report.detail].filter(Boolean).join("\n"));
  }

  if (!review) {
    return (
      <section className="review-panel detail">
        <h2>Review</h2>
        <p className="quiet">Comparing the draft with dev…</p>
      </section>
    );
  }

  const blocked = review.errors.length > 0;

  return (
    <section className="review-panel detail" id="review-panel" aria-label="Review and publish">
      <header className="detail-head">
        <h2>Review</h2>
        <p>{review.summary.join(" ")}</p>
      </header>
      {blocked ? (
        <p className="issue error">Publishing is blocked until {review.errors.length} validation error{review.errors.length === 1 ? "" : "s"} are fixed.</p>
      ) : (
        <p className="quiet">Publishing opens a pull request into dev. It does not upload to the conference server.</p>
      )}
      <pre className="diff">{review.diff || "No file diff."}</pre>
      <div className="dialog-actions">
        <button
          type="button"
          className="text-button pressable"
          disabled={busy}
          onClick={() => {
            setBusy(true);
            openPreview()
              .then((result) => {
                window.open(result.url, "_blank", "noopener");
              })
              .catch((error: unknown) => {
                toast.error(error instanceof Error ? error.message : "Preview failed");
              })
              .finally(() => setBusy(false));
          }}
        >
          Preview site
        </button>
        <button
          type="button"
          className="save pressable"
          id="btn-publish"
          disabled={busy || blocked}
          onClick={() => {
            setBusy(true);
            publishProgramme()
              .then(async (result) => {
                setPublished(result);
                toast.success(result.pull_request ? "Pull request opened" : "Compare URL ready");
                if (result.pull_request) {
                  await refreshStatus(result.pull_request);
                } else {
                  setChecks(result.detail || result.compare_url);
                }
              })
              .catch((error: unknown) => {
                toast.error(error instanceof Error ? error.message : "Publish failed");
              })
              .finally(() => setBusy(false));
          }}
        >
          {busy ? "Working…" : "Publish to dev"}
        </button>
      </div>
      {published ? (
        <div className="publish-result">
          <p>
            Branch <code>{published.branch}</code>
          </p>
          {published.pull_request ? (
            <p>
              <a href={published.pull_request} target="_blank" rel="noreferrer">
                {published.pull_request}
              </a>
            </p>
          ) : (
            <p>
              <a href={published.compare_url} target="_blank" rel="noreferrer">
                {published.compare_url}
              </a>
            </p>
          )}
          {checks ? <pre className="diff">{checks}</pre> : null}
          {published.pull_request ? (
            <button type="button" className="text-button pressable" onClick={() => void refreshStatus(published.pull_request || "")}>
              Refresh CI status
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
