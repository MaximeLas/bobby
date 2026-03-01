import './Stats.css';

export default function Stats() {
  const stats = [
    { number: '50K+', label: 'Active Users' },
    { number: '1M+', label: 'Projects Created' },
    { number: '99.9%', label: 'Uptime' },
    { number: '500+', label: 'Companies' }
  ];

  return (
    <section className="stats-section">
      <div className="stats-container">
        <h2 className="stats-heading">By the numbers</h2>
        <div className="stats-grid">
          {stats.map((stat, index) => (
            <div key={index} className="stat-item">
              <div className="stat-number">{stat.number}</div>
              <div className="stat-label">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
