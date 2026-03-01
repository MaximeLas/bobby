import './Comparison.css';

export default function Comparison() {
  const features = [
    { name: 'Unlimited projects', flowtask: true, asana: true, trello: false },
    { name: 'Advanced automation', flowtask: true, asana: true, trello: false },
    { name: 'Custom workflows', flowtask: true, asana: false, trello: false },
    { name: 'Real-time collaboration', flowtask: true, asana: true, trello: true },
    { name: 'Time tracking built-in', flowtask: true, asana: false, trello: false },
    { name: 'Unlimited integrations', flowtask: true, asana: false, trello: true },
    { name: 'Priority support 24/7', flowtask: true, asana: false, trello: false },
    { name: 'Free plan available', flowtask: true, asana: true, trello: true },
  ];

  return (
    <section className="comparison">
      <div className="comparison-container">
        <h2 className="comparison-heading">How we compare</h2>
        <div className="comparison-table-wrapper">
          <table className="comparison-table">
            <thead>
              <tr>
                <th className="feature-column">Feature</th>
                <th className="product-column flowtask-column">
                  <div className="product-header">
                    <span className="product-name">FlowTask</span>
                    <span className="badge">Best Value</span>
                  </div>
                </th>
                <th className="product-column">Asana</th>
                <th className="product-column">Trello</th>
              </tr>
            </thead>
            <tbody>
              {features.map((feature, index) => (
                <tr key={index}>
                  <td className="feature-name">{feature.name}</td>
                  <td className="flowtask-cell">
                    {feature.flowtask ? (
                      <span className="checkmark">✓</span>
                    ) : (
                      <span className="cross">—</span>
                    )}
                  </td>
                  <td>
                    {feature.asana ? (
                      <span className="checkmark">✓</span>
                    ) : (
                      <span className="cross">—</span>
                    )}
                  </td>
                  <td>
                    {feature.trello ? (
                      <span className="checkmark">✓</span>
                    ) : (
                      <span className="cross">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
