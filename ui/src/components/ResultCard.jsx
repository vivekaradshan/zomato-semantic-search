export default function ResultCard({ result, rank }) {
  const rating = parseFloat(result.rating) || 0;
  const stars   = "★".repeat(Math.round(rating)) +
                  "☆".repeat(5 - Math.round(rating));

  return (
    <div className="result-card">
      <div className="card-rank">#{rank}</div>
      <div className="card-body">
        <h3 className="card-name">{result.name}</h3>
        <p className="card-cuisines">{result.cuisines}</p>
        <div className="card-footer">
          <span className="card-rating">
            <span className="stars">{stars}</span>
            <span className="rating-num">{rating.toFixed(1)}</span>
          </span>
          {result.location && (
            <span className="card-location">📍 {result.location}</span>
          )}
        </div>
      </div>
    </div>
  );
}
