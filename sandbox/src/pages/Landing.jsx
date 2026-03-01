import Hero from '../components/Hero';
import LogoSection from '../components/LogoSection';
import Stats from '../components/Stats';
import Features from '../components/Features';
import Comparison from '../components/Comparison';
import Pricing from '../components/Pricing';
import FAQ from '../components/FAQ';
import Newsletter from '../components/Newsletter';
import CTA from '../components/CTA';
import Footer from '../components/Footer';
import './Landing.css';

export default function Landing() {
  return (
    <div className="landing">
      <Hero />
      <LogoSection />
      <Stats />
      <Features />
      <Comparison />
      <Pricing />
      <section className="about">
        <div className="about-container">
          <h2 className="about-heading">Built for modern teams</h2>
          <p className="about-text">
            FlowTask was created by a team that understands the challenges of managing complex projects.
            We've worked in startups, agencies, and enterprise companies, and we know what it takes to keep
            teams aligned and productive.
          </p>
          <p className="about-text">
            Our mission is simple: make task management effortless so teams can focus on doing their best work.
            With FlowTask, you get a powerful yet intuitive platform that grows with your team.
          </p>
        </div>
      </section>
      <FAQ />
      <Newsletter />
      <CTA />
      <Footer />
    </div>
  );
}
