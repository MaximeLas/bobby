import './CTA.css';

export default function CTA() {
  return (
    <section className="cta">
      <div className="cta-container">
        <h2 className="cta-heading">Ready to get started?</h2>
        <p className="cta-subheading">
          Join thousands of teams already using FlowTask to ship faster and work smarter.
        </p>
        <button className="cta-button">Start for free</button>
        <p className="cta-disclaimer">No credit card required</p>
      </div>
    </section>
  );
}
