import { Cpu, Layers, Eye, Database, AlertTriangle, GitBranch } from 'lucide-react';
import { useApp } from '../context/AppContext';

export function ModelInfoPage() {
  const { healthData } = useApp();
  const steps = [
    ['Image input', 'RGB upload', 'JPG, JPEG, PNG or WEBP, up to 10 MB. The server validates the image bytes.'],
    ['Preprocessing', '224 × 224 × 3', 'RGB float32 input retains the 0–255 range. The saved model contains its own rescaling.'],
    ['Feature extraction', 'EfficientNetB0', 'The actual trained Keras artifact supplies convolutional features. No random replacement head is used.'],
    ['Classification head', 'Binary sigmoid', 'The saved classifier returns a real-image score. Its fake score is one minus that value.'],
    ['Decision rule', healthData?.threshold != null ? `Real threshold: ${healthData.threshold}` : 'Threshold unavailable', 'REAL when real score ≥ configured threshold; otherwise FAKE. The API label is authoritative.'],
    ['Grad-CAM', 'Relative attention', 'Gradients for the selected class produce an attention map and an overlay when the model graph supports it.'],
    ['History', 'Metadata only', 'Prediction, scores, filename, threshold and timing are saved. Uploaded pixels and generated images are not retained.'],
  ];
  const pillars = [
    { title: 'EfficientNetB0 architecture', Icon: Cpu, color: 'text-[#21D4FD]', text: 'EfficientNet combines mobile inverted bottleneck convolution blocks and squeeze-and-excitation with compound scaling. This application uses a saved binary classifier based on that backbone; the backend loads the existing model rather than training in the browser.' },
    { title: 'Model scores & threshold', Icon: Layers, color: 'text-[#8B5CF6]', text: 'The configured threshold is applied to the real score, not the fake score. A non-0.5 threshold means the predicted class need not have the larger displayed score. Confidence is the score for the chosen class, not a measured likelihood that the decision is correct.' },
    { title: 'Grad-CAM interpretation', Icon: Eye, color: 'text-[#10B981]', text: 'Grad-CAM highlights coarse regions relevant to the model’s selected class. The separate heatmap uses pale-to-dark blue for lower-to-higher relative attention. It is not a segmentation mask or evidence that a highlighted region was manipulated. Missing positive activation is reported rather than painted as a meaningless overlay.' },
    { title: 'Evaluation & data provenance', Icon: Database, color: 'text-[#F59E0B]', text: 'The project has labeled dataset files, retraining records and a separate frozen-test evaluation workspace. Evaluation results are specific to the recorded model hash, threshold and split; they are not live deployment accuracy or proof of authenticity. The application continues to use the production model unless separately approved. Original training provenance and related image identities still limit generalization claims.' },
  ];
  return <div className="space-y-6 max-w-5xl mx-auto">
    <div><span className="inline-flex items-center gap-2 text-xs text-[#21D4FD] px-3 py-1 rounded-full bg-[#21D4FD]/10 border border-[#21D4FD]/30 mb-3"><Cpu size={13} />Model documentation</span><h2 className="text-2xl sm:text-3xl font-extrabold">Understanding Our Detection Engine</h2><p className="text-sm text-[#94A3B8] mt-2">The trained model, its decision rule, and the limits of explainable image forensics.</p></div>
    <section className="panel sm:p-6"><h3 className="flex items-center gap-2 text-sm font-bold uppercase"><GitBranch size={17} className="text-[#21D4FD]" />End-to-end inference architecture</h3><ol className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mt-5">{steps.map(([title, spec, text], index) => <li key={title} className="p-4 bg-[#080D18] border border-[#243247] rounded-xl"><p className="text-[10px] font-mono text-[#94A3B8]">STAGE {index + 1}</p><h4 className="text-xs font-bold mt-1">{title}</h4><p className="text-[11px] text-[#21D4FD] font-mono mt-2">{spec}</p><p className="text-[11px] text-[#94A3B8] leading-relaxed mt-2">{text}</p></li>)}</ol></section>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">{pillars.map(({ title, Icon, color, text }) => <section className="panel sm:p-6 space-y-3" key={title}><div className={`p-2.5 w-fit bg-[#152238] rounded-lg border border-[#243247] ${color}`}><Icon size={20} /></div><h3 className="font-bold text-base">{title}</h3><p className="text-xs leading-relaxed text-[#94A3B8]">{text}</p></section>)}</div>
    <section className="panel bg-[#0B1220] space-y-4"><h3 className="flex items-center gap-2 font-bold text-sm"><AlertTriangle size={18} className="text-[#F59E0B]" />Model limitations & forensic boundaries</h3><div className="grid grid-cols-1 sm:grid-cols-2 gap-4">{[
      ['Compression & resizing', 'Recompression, blurring and downscaling can remove information that a classifier relies on.'],
      ['Distribution shift', 'Images or generation techniques unlike the training distribution can produce confident mistakes.'],
      ['Limited explanation', 'Attention shows sensitivity in the model, not causality or proof of tampering.'],
      ['Decision support only', 'Use independent evidence and qualified review for consequential decisions.'],
    ].map(([title, text]) => <div key={title} className="p-3 bg-[#111B2D] rounded-lg border border-[#243247]"><h4 className="text-xs font-semibold">{title}</h4><p className="text-[11px] text-[#94A3B8] mt-1 leading-relaxed">{text}</p></div>)}</div></section>
  </div>;
}
