import type {Metadata} from 'next';
import './globals.css';
import './editor.css';
export const metadata:Metadata={title:'StoryCast Studio',description:'Evidence-backed news video studio'};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
