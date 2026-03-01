import Button from './Button';
import './Hero.css';

export default function Hero() {
  return (
    <section className="hero">
      <div className="hero-content">
        <h1 className="hero-title">Build and ship smarter, not just faster.</h1>
        <p className="hero-subtitle">
          FlowTask helps teams organize work, track progress, and collaborate seamlessly.
          Everything your team needs to stay productive in one place.
        </p>
        <div className="hero-buttons">
          <Button variant="primary">Start Building</Button>
          <Button variant="secondary">Watch Demo</Button>
        </div>
      </div>
    </section>
  );
}
