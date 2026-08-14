import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import type { ForecastResponse } from "./api";

export async function exportForecastPdf(reportEl: HTMLElement, forecast: ForecastResponse) {
  const canvas = await html2canvas(reportEl, {
    backgroundColor: "#0c0e12",
    scale: 2,
  });
  const imgData = canvas.toDataURL("image/png");

  const pdf = new jsPDF({ orientation: "portrait", unit: "pt", format: "a4" });
  const pageWidth = pdf.internal.pageSize.getWidth();
  const margin = 32;

  pdf.setFillColor(12, 14, 18);
  pdf.rect(0, 0, pageWidth, pdf.internal.pageSize.getHeight(), "F");

  pdf.setTextColor(243, 243, 239);
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(18);
  pdf.text("WindCast", margin, 48);

  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(10);
  pdf.setTextColor(154, 160, 172);
  pdf.text(
    `${forecast.location.name} · ${forecast.location.lat.toFixed(3)}, ${forecast.location.lon.toFixed(3)} · ${new Date().toLocaleString()}`,
    margin,
    66
  );

  const imgWidth = pageWidth - margin * 2;
  const imgHeight = (canvas.height * imgWidth) / canvas.width;
  pdf.addImage(imgData, "PNG", margin, 84, imgWidth, imgHeight);

  let y = 84 + imgHeight + 28;
  pdf.setFontSize(12);
  pdf.setTextColor(243, 243, 239);
  pdf.setFont("helvetica", "bold");
  pdf.text("Métriques validées (MAE / RMSE / MAPE / R²)", margin, y);
  y += 18;
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(10);
  pdf.setTextColor(154, 160, 172);
  const m = forecast.metrics;
  pdf.text(
    `MAE ${m.mae ?? "n/a"} m/s · RMSE ${m.rmse ?? "n/a"} m/s · MAPE ${m.mape_unavailable ? "indisponible" : `${m.mape}%`} · R² ${m.r2 ?? "n/a"} — validé sur ${m.validated_on}`,
    margin,
    y
  );
  y += 20;
  pdf.text(
    `Confiance : ${Math.round(forecast.confidence.score * 100)}% (${forecast.confidence.label}) — ${forecast.confidence.reason}`,
    margin,
    y,
    { maxWidth: pageWidth - margin * 2 }
  );

  pdf.save(`windcast-${forecast.location.name.replace(/\s+/g, "-").toLowerCase()}.pdf`);
}
