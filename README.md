<img width="104" height="150" alt="lead_enrichment_pipeline_sequence" src="https://github.com/user-attachments/assets/640849b1-3ccf-42f1-b6b4-7952e393dfbd" /># Lead Intelligence & Enrichment Engine

An autonomous, concurrent web intelligence, and optionally deploy an autonomous browser agent to discover timely trigger events.

Built with Python 3.11+, Playwright, Instructor, Pydantic, and Browser-Use.

---

![Uploading le<svg width="100%" viewBox="0 0 680 980" role="img" style="" xmlns="http://www.w3.org/2000/svg" xmlns:c2pa="http://c2pa.org/manifest"><metadata><c2pa:manifest>AAAWkGp1bWIAAAAeanVtZGMycGEAEQAQgAAAqgA4m3EDYzJwYQAAABZqanVtYgAAAEdqdW1kYzJtYQARABCAAACqADibcQN1cm46YzJwYTowMmVlNTdmZC03NDkyLTQyNmMtODk1ZC0wNDhlYjg5NTdkNWIAAAADf2p1bWIAAAApanVtZGMyYXMAEQAQgAAAqgA4m3EDYzJwYS5hc3NlcnRpb25zAAAAALxqdW1iAAAARGp1bWRjYm9yABEAEIAAAKoAOJtxE2MycGEuaW5ncmVkaWVudC52MwAAAAAYYzJzaAs5kakrJ1GTjQboqWRrGi0AAABwY2JvcqNscmVsYXRpb25zaGlwaHBhcmVudE9maWRjOmZvcm1hdG1pbWFnZS9zdmcreG1samluc3RhbmNlSUR4LHhtcDppaWQ6M2IwNDUzODYtOTNiYS00NDlhLWIxMjgtNTliNWVjNjI0NjMzAAABzmp1bWIAAABBanVtZGNib3IAEQAQgAAAqgA4m3ETYzJwYS5hY3Rpb25zLnYyAAAAABhjMnNoon1SxTC/dXEFucoqBreCpQAAAYVjYm9yoWdhY3Rpb25zgqJmYWN0aW9ua2MycGEub3BlbmVkanBhcmFtZXRlcnOha2luZ3JlZGllbnRzgaJjdXJseC1zZWxmI2p1bWJmPWMycGEuYXNzZXJ0aW9ucy9jMnBhLmluZ3JlZGllbnQudjNkaGFzaFggyS4rqa4ZXvEt4ViFzm8DKbWFKpJaLKUHukCvPN8x566kZmFjdGlvbngdY29tLmFudGhyb3BpYy5jbGF1ZGUucHJvdmlkZWRtc29mdHdhcmVBZ2VudKFkbmFtZWZDbGF1ZGVqcGFyYW1ldGVyc6F4H2NvbS5hbnRocm9waWMub3JpZ2luLWNvbmZpZGVuY2VndW5rbm93bmtkZXNjcmlwdGlvbnhmQ2xhdWRlIHByb3ZpZGVkIHRoaXMgZmlsZSBhdCB0aGUgcmVxdWVzdCBvZiBhIHVzZXIgYW5kIG1heSBoYXZlIGNyZWF0ZWQgb3IgbW9kaWZpZWQgdGhlIGZpbGUgY29udGVudHMuAAAAxGp1bWIAAABAanVtZGNib3IAEQAQgAAAqgA4m3ETYzJwYS5oYXNoLmRhdGEAAAAAGGMyc2it9aEbZnEtm7Pire12n9O4AAAAfGNib3KlamV4Y2x1c2lvbnOBomVzdGFydBieZmxlbmd0aBkeGGRuYW1lbmp1bWJmIG1hbmlmZXN0Y2FsZ2ZzaGEyNTZkaGFzaFggxCD/mhbmtyI7Np9UMWy/ewnM++IjCS9fNt653Z3dWDVjcGFkSQAAAAAAAAAAAAAAAmRqdW1iAAAAJ2p1bWRjMmNsABEAEIAAAKoAOJtxA2MycGEuY2xhaW0udjIAAAACNWNib3Kmamluc3RhbmNlSUR4LHhtcDppaWQ6NzdhZDIzNjctYTdkYi00OWE5LTg3ZTUtY2QzNWUzNDlmM2Q1dGNsYWltX2dlbmVyYXRvcl9pbmZvo2RuYW1lc0FudGhyb3BpYyBDbGF1ZGUuYWlndmVyc2lvbmUxLjAuMHdvcmcuY29udGVudGF1dGguYzJwYV9yc2YwLjkwLjBpc2lnbmF0dXJleE1zZWxmI2p1bWJmPS9jMnBhL3VybjpjMnBhOjAyZWU1N2ZkLTc0OTItNDI2Yy04OTVkLTA0OGViODk1N2Q1Yi9jMnBhLnNpZ25hdHVyZXJjcmVhdGVkX2Fzc2VydGlvbnOComN1cmx4KnNlbGYjanVtYmY9YzJwYS5hc3NlcnRpb25zL2MycGEuYWN0aW9ucy52MmRoYXNoWCBjD1rti4jS4crzy61HH6Lb7UqyfpJ66Eof78A0WJzxBqJjdXJseClzZWxmI2p1bWJmPWMycGEuYXNzZXJ0aW9ucy9jMnBhLmhhc2guZGF0YWRoYXNoWCCOWQZWr7kTbFJRiatXxfYPEliUAdryc8A1UhO9aQTPx3NnYXRoZXJlZF9hc3NlcnRpb25zgaJjdXJseC1zZWxmI2p1bWJmPWMycGEuYXNzZXJ0aW9ucy9jMnBhLmluZ3JlZGllbnQudjNkaGFzaFggyS4rqa4ZXvEt4ViFzm8DKbWFKpJaLKUHukCvPN8x565jYWxnZnNoYTI1NgAAEDhqdW1iAAAAKGp1bWRjMmNzABEAEIAAAKoAOJtxA2MycGEuc2lnbmF0dXJlAAAAEAhjYm9y0oRZAhKiASYYIVkCCjCCAgYwggGNoAMCAQICFEDloAruwjnQvriD+gZCBT1nVRMAMAoGCCqGSM49BAMDMEkxFzAVBgNVBAoTDkFudGhyb3BpYywgUEJDMS4wLAYDVQQDEyVBbnRocm9waWMgQ29udGVudCBDcmVkZW50aWFscyBSb290IENBMB4XDTI2MDgwNzE4NDM1NloXDTI4MDgwNjE5NDM1NlowRDEXMBUGA1UEChMOQW50aHJvcGljLCBQQkMxKTAnBgNVBAMTIEFudGhyb3BpYyBDbGF1ZGUgQ29udGVudCBTaWduaW5nMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEmHoKa8tQGAUU1TS9QqU5W0Tp2N3XsvlK7BfQt6YWKwEzd2R3/dzKPEUDdCjlLjp9fT+KFjRVnuZ9v0oXvTe3k6NYMFYwDgYDVR0PAQH/BAQDAgeAMBUGA1UdJQQOMAwGCisGAQQBg+heAgEwDAYDVR0TAQH/BAIwADAfBgNVHSMEGDAWgBTOUeIEgU5kWyP448TPmj6cwddcwjAKBggqhkjOPQQDAwNnADBkAjAxcx0UngF60stVjs5G4T2eiptsBk5mf9oCtfJPAUBl8qs/PEXa8+gk1/X5QJ2DVcYCMHBfXN31YapiSqYvlIWrDVDJKOvXMl+kkz37Wt0PBI8sw486Mq6JeOhT+lRR4b1HCaFjcGFkWQ2eAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA9lhAk2D/fhV1EJLZOHdNYAMhNqQMlWX10dpLen/jq3/yhRSjpYw5IZPOkOcdepbtKuwZY2H3B8mMSU3xWOGCP0JeRA==</c2pa:manifest></metadata>
<title style="fill:rgb(0, 0, 0);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto">Lead enrichment pipeline sequence diagram</title>
<desc style="fill:rgb(0, 0, 0);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto">Sequence diagram showing User, CLI, Pipeline orchestrator, Browser, LLM, and Enricher interacting through the per-domain enrichment loop.</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></marker><mask id="imagine-text-gaps-fi2vsl" maskUnits="userSpaceOnUse"><rect x="0" y="0" width="680" height="980" fill="white"/><rect x="65.46062469482422" y="31.589141845703125" width="39.078744888305664" height="20.82170867919922" fill="black" rx="2"/><rect x="170.1280059814453" y="31.589141845703125" width="29.74397087097168" height="20.82170867919922" fill="black" rx="2"/><rect x="254.8753662109375" y="31.589141845703125" width="60.24924850463867" height="20.82170867919922" fill="black" rx="2"/><rect x="353.9713439941406" y="31.589141845703125" width="62.0572624206543" height="20.82170867919922" fill="black" rx="2"/><rect x="466.9579772949219" y="31.589141845703125" width="36.08397102355957" height="20.82170867919922" fill="black" rx="2"/><rect x="553.5093994140625" y="31.589141845703125" width="62.98118209838867" height="20.82170867919922" fill="black" rx="2"/><rect x="90.47895050048828" y="82.27577209472656" width="89.04208374023438" height="18.27296543121338" fill="black" rx="2"/><rect x="179.99325561523438" y="134.2757568359375" width="110.01347351074219" height="18.27296543121338" fill="black" rx="2"/><rect x="250.99998474121094" y="176.2367706298828" width="140.3594512939453" height="20.82170867919922" fill="black" rx="2"/><rect x="250.99998474121094" y="196.2757568359375" width="145.1781768798828" height="18.27296543121338" fill="black" rx="2"/><rect x="296" y="208.27577209472656" width="83.13218688964844" height="18.27296543121338" fill="black" rx="2"/><rect x="295.75164794921875" y="264.2757873535156" width="78.49665832519531" height="18.27296543121338" fill="black" rx="2"/><rect x="395.9999694824219" y="312.2757568359375" width="89.58369445800781" height="18.27296543121338" fill="black" rx="2"/><rect x="293.6091003417969" y="368.2757568359375" width="82.78173828125" height="18.27296543121338" fill="black" rx="2"/><rect x="317.0145568847656" y="420.2757568359375" width="135.97083282470703" height="18.27296543121338" fill="black" rx="2"/><rect x="337.762939453125" y="472.2757568359375" width="94.4740982055664" height="18.27296543121338" fill="black" rx="2"/><rect x="374.37799072265625" y="524.2757568359375" width="121.2438735961914" height="18.27296543121338" fill="black" rx="2"/><rect x="368.8663330078125" y="576.2757568359375" width="132.2671890258789" height="18.27296543121338" fill="black" rx="2"/><rect x="296" y="624.2757568359375" width="127.02633666992188" height="18.27296543121338" fill="black" rx="2"/><rect x="320.2140808105469" y="700.2757568359375" width="233.57179260253906" height="18.27296543121338" fill="black" rx="2"/><rect x="191.98031616210938" y="738.2756958007812" width="86.03935241699219" height="18.27296543121338" fill="black" rx="2"/><rect x="220.99998474121094" y="786.2757568359375" width="105.08325958251953" height="18.27296543121338" fill="black" rx="2"/><rect x="65.88756561279297" y="842.2757568359375" width="138.22488403320312" height="18.27296543121338" fill="black" rx="2"/><rect x="65.46062469482422" y="915.5890502929688" width="39.078744888305664" height="20.82170867919922" fill="black" rx="2"/><rect x="170.1280059814453" y="915.5890502929688" width="29.74397087097168" height="20.82170867919922" fill="black" rx="2"/><rect x="254.8753662109375" y="915.5890502929688" width="60.24924850463867" height="20.82170867919922" fill="black" rx="2"/><rect x="353.9713439941406" y="915.5890502929688" width="62.0572624206543" height="20.82170867919922" fill="black" rx="2"/><rect x="466.9579772949219" y="915.5890502929688" width="36.08397102355957" height="20.82170867919922" fill="black" rx="2"/><rect x="553.5093994140625" y="915.5890502929688" width="62.98118209838867" height="20.82170867919922" fill="black" rx="2"/></mask></defs>

<line x1="85" y1="64" x2="85" y2="904" stroke="var(--border-strong)" stroke-width="0.5" mask="url(#imagine-text-gaps-fi2vsl)" style="fill:rgb(0, 0, 0);stroke:color(srgb 0.0431373 0.0431373 0.0431373 / 0.2);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<line x1="185" y1="64" x2="185" y2="904" stroke="var(--border-strong)" stroke-width="0.5" mask="url(#imagine-text-gaps-fi2vsl)" style="fill:rgb(0, 0, 0);stroke:color(srgb 0.0431373 0.0431373 0.0431373 / 0.2);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<line x1="285" y1="64" x2="285" y2="904" stroke="var(--border-strong)" stroke-width="0.5" mask="url(#imagine-text-gaps-fi2vsl)" style="fill:rgb(0, 0, 0);stroke:color(srgb 0.0431373 0.0431373 0.0431373 / 0.2);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<line x1="385" y1="64" x2="385" y2="904" stroke="var(--border-strong)" stroke-width="0.5" mask="url(#imagine-text-gaps-fi2vsl)" style="fill:rgb(0, 0, 0);stroke:color(srgb 0.0431373 0.0431373 0.0431373 / 0.2);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<line x1="485" y1="64" x2="485" y2="904" stroke="var(--border-strong)" stroke-width="0.5" mask="url(#imagine-text-gaps-fi2vsl)" style="fill:rgb(0, 0, 0);stroke:color(srgb 0.0431373 0.0431373 0.0431373 / 0.2);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<line x1="585" y1="64" x2="585" y2="904" stroke="var(--border-strong)" stroke-width="0.5" style="fill:rgb(0, 0, 0);stroke:color(srgb 0.0431373 0.0431373 0.0431373 / 0.2);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>

<g style="fill:rgb(0, 0, 0);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"><rect x="40" y="20" width="90" height="44" rx="8" stroke-width="0.5" style="fill:rgb(241, 239, 232);stroke:rgb(95, 94, 90);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/><text x="85" y="42" text-anchor="middle" dominant-baseline="central" style="fill:rgb(68, 68, 65);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:14px;font-weight:500;text-anchor:middle;dominant-baseline:central">User</text></g>
<g style="fill:rgb(0, 0, 0);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"><rect x="140" y="20" width="90" height="44" rx="8" stroke-width="0.5" style="fill:rgb(225, 245, 238);stroke:rgb(15, 110, 86);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/><text x="185" y="42" text-anchor="middle" dominant-baseline="central" style="fill:rgb(8, 80, 65);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:14px;font-weight:500;text-anchor:middle;dominant-baseline:central">CLI</text></g>
<g style="fill:rgb(0, 0, 0);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"><rect x="240" y="20" width="90" height="44" rx="8" stroke-width="0.5" style="fill:rgb(225, 245, 238);stroke:rgb(15, 110, 86);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/><text x="285" y="42" text-anchor="middle" dominant-baseline="central" style="fill:rgb(8, 80, 65);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:14px;font-weight:500;text-anchor:middle;dominant-baseline:central">Pipeline</text></g>
<g style="fill:rgb(0, 0, 0);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"><rect x="340" y="20" width="90" height="44" rx="8" stroke-width="0.5" style="fill:rgb(225, 245, 238);stroke:rgb(15, 110, 86);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/><text x="385" y="42" text-anchor="middle" dominant-baseline="central" style="fill:rgb(8, 80, 65);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:14px;font-weight:500;text-anchor:middle;dominant-baseline:central">Browser</text></g>
<g style="fill:rgb(0, 0, 0);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"><rect x="440" y="20" width="90" height="44" rx="8" stroke-width="0.5" style="fill:rgb(225, 245, 238);stroke:rgb(15, 110, 86);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/><text x="485" y="42" text-anchor="middle" dominant-baseline="central" style="fill:rgb(8, 80, 65);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:14px;font-weight:500;text-anchor:middle;dominant-baseline:central">LLM</text></g>
<g style="fill:rgb(0, 0, 0);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"><rect x="540" y="20" width="90" height="44" rx="8" stroke-width="0.5" style="fill:rgb(225, 245, 238);stroke:rgb(15, 110, 86);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/><text x="585" y="42" text-anchor="middle" dominant-baseline="central" style="fill:rgb(8, 80, 65);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:14px;font-weight:500;text-anchor:middle;dominant-baseline:central">Enricher</text></g>

<line x1="85" y1="104" x2="185" y2="104" marker-end="url(#arrow)" style="fill:none;stroke:rgb(137, 135, 129);color:rgb(11, 11, 11);stroke-width:1.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<text x="135" y="96" text-anchor="middle" style="fill:rgb(82, 81, 78);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:12px;font-weight:400;text-anchor:middle;dominant-baseline:auto">run --domains</text>

<line x1="185" y1="156" x2="285" y2="156" marker-end="url(#arrow)" style="fill:none;stroke:rgb(137, 135, 129);color:rgb(11, 11, 11);stroke-width:1.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<text x="235" y="148" text-anchor="middle" style="fill:rgb(82, 81, 78);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:12px;font-weight:400;text-anchor:middle;dominant-baseline:auto">process_domain()</text>

<rect x="235" y="168" width="405" height="526" rx="12" fill="none" stroke="var(--border-strong)" stroke-width="0.5" stroke-dasharray="4 3" style="fill:none;stroke:color(srgb 0.0431373 0.0431373 0.0431373 / 0.2);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-dasharray:4px, 3px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<text x="255" y="192" style="fill:rgb(11, 11, 11);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:14px;font-weight:500;text-anchor:start;dominant-baseline:auto">Per-domain pipeline</text>
<text x="255" y="210" style="fill:rgb(82, 81, 78);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:12px;font-weight:400;text-anchor:start;dominant-baseline:auto">repeats for each domain</text>

<path d="M285 234 C 325 234 325 268 285 268" fill="none" marker-end="url(#arrow)" mask="url(#imagine-text-gaps-fi2vsl)" style="fill:none;stroke:rgb(137, 135, 129);color:rgb(11, 11, 11);stroke-width:1.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<text x="300" y="222" style="fill:rgb(82, 81, 78);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:12px;font-weight:400;text-anchor:start;dominant-baseline:auto">discover_urls</text>

<line x1="285" y1="286" x2="385" y2="286" marker-end="url(#arrow)" style="fill:none;stroke:rgb(137, 135, 129);color:rgb(11, 11, 11);stroke-width:1.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<text x="335" y="278" text-anchor="middle" style="fill:rgb(82, 81, 78);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:12px;font-weight:400;text-anchor:middle;dominant-baseline:auto">fetch_pages</text>

<path d="M385 338 C 425 338 425 372 385 372" fill="none" marker-end="url(#arrow)" style="fill:none;stroke:rgb(137, 135, 129);color:rgb(11, 11, 11);stroke-width:1.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<text x="400" y="326" style="fill:rgb(82, 81, 78);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:12px;font-weight:400;text-anchor:start;dominant-baseline:auto">render + clean</text>

<line x1="385" y1="390" x2="285" y2="390" marker-end="url(#arrow)" style="fill:none;stroke:rgb(137, 135, 129);color:rgb(11, 11, 11);stroke-width:1.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<text x="335" y="382" text-anchor="middle" style="fill:rgb(82, 81, 78);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:12px;font-weight:400;text-anchor:middle;dominant-baseline:auto">page content</text>

<line x1="285" y1="442" x2="485" y2="442" marker-end="url(#arrow)" style="fill:none;stroke:rgb(137, 135, 129);color:rgb(11, 11, 11);stroke-width:1.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<text x="385" y="434" text-anchor="middle" style="fill:rgb(82, 81, 78);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:12px;font-weight:400;text-anchor:middle;dominant-baseline:auto">extract_company_intel</text>

<line x1="485" y1="494" x2="285" y2="494" marker-end="url(#arrow)" style="fill:none;stroke:rgb(137, 135, 129);color:rgb(11, 11, 11);stroke-width:1.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<text x="385" y="486" text-anchor="middle" style="fill:rgb(82, 81, 78);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:12px;font-weight:400;text-anchor:middle;dominant-baseline:auto">structured intel</text>

<line x1="285" y1="546" x2="585" y2="546" marker-end="url(#arrow)" style="fill:none;stroke:rgb(137, 135, 129);color:rgb(11, 11, 11);stroke-width:1.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<text x="435" y="538" text-anchor="middle" style="fill:rgb(82, 81, 78);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:12px;font-weight:400;text-anchor:middle;dominant-baseline:auto">enrich_linkedin_urls</text>

<line x1="585" y1="598" x2="285" y2="598" marker-end="url(#arrow)" style="fill:none;stroke:rgb(137, 135, 129);color:rgb(11, 11, 11);stroke-width:1.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<text x="435" y="590" text-anchor="middle" style="fill:rgb(82, 81, 78);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:12px;font-weight:400;text-anchor:middle;dominant-baseline:auto">verified team + emails</text>

<path d="M285 650 C 325 650 325 684 285 684" fill="none" marker-end="url(#arrow)" style="fill:none;stroke:rgb(137, 135, 129);color:rgb(11, 11, 11);stroke-width:1.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<text x="300" y="638" style="fill:rgb(82, 81, 78);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:12px;font-weight:400;text-anchor:start;dominant-baseline:auto">compute_confidence</text>

<text x="437" y="714" text-anchor="middle" style="fill:rgb(82, 81, 78);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:12px;font-weight:400;text-anchor:middle;dominant-baseline:auto">↻ loop continues for remaining domains</text>

<line x1="285" y1="760" x2="185" y2="760" marker-end="url(#arrow)" style="fill:none;stroke:rgb(137, 135, 129);color:rgb(11, 11, 11);stroke-width:1.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<text x="235" y="752" text-anchor="middle" style="fill:rgb(82, 81, 78);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:12px;font-weight:400;text-anchor:middle;dominant-baseline:auto">DomainResult</text>

<path d="M185 812 C 225 812 225 846 185 846" fill="none" marker-end="url(#arrow)" mask="url(#imagine-text-gaps-fi2vsl)" style="fill:none;stroke:rgb(137, 135, 129);color:rgb(11, 11, 11);stroke-width:1.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<text x="225" y="800" style="fill:rgb(82, 81, 78);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:12px;font-weight:400;text-anchor:start;dominant-baseline:auto">write_run_output</text>

<line x1="185" y1="864" x2="85" y2="864" marker-end="url(#arrow)" style="fill:none;stroke:rgb(137, 135, 129);color:rgb(11, 11, 11);stroke-width:1.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/>
<text x="135" y="856" text-anchor="middle" style="fill:rgb(82, 81, 78);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:12px;font-weight:400;text-anchor:middle;dominant-baseline:auto">summary + output files</text>

<g style="fill:rgb(0, 0, 0);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"><rect x="40" y="904" width="90" height="44" rx="8" stroke-width="0.5" style="fill:rgb(241, 239, 232);stroke:rgb(95, 94, 90);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/><text x="85" y="926" text-anchor="middle" dominant-baseline="central" style="fill:rgb(68, 68, 65);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:14px;font-weight:500;text-anchor:middle;dominant-baseline:central">User</text></g>
<g style="fill:rgb(0, 0, 0);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"><rect x="140" y="904" width="90" height="44" rx="8" stroke-width="0.5" style="fill:rgb(225, 245, 238);stroke:rgb(15, 110, 86);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/><text x="185" y="926" text-anchor="middle" dominant-baseline="central" style="fill:rgb(8, 80, 65);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:14px;font-weight:500;text-anchor:middle;dominant-baseline:central">CLI</text></g>
<g style="fill:rgb(0, 0, 0);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"><rect x="240" y="904" width="90" height="44" rx="8" stroke-width="0.5" style="fill:rgb(225, 245, 238);stroke:rgb(15, 110, 86);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/><text x="285" y="926" text-anchor="middle" dominant-baseline="central" style="fill:rgb(8, 80, 65);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:14px;font-weight:500;text-anchor:middle;dominant-baseline:central">Pipeline</text></g>
<g style="fill:rgb(0, 0, 0);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"><rect x="340" y="904" width="90" height="44" rx="8" stroke-width="0.5" style="fill:rgb(225, 245, 238);stroke:rgb(15, 110, 86);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/><text x="385" y="926" text-anchor="middle" dominant-baseline="central" style="fill:rgb(8, 80, 65);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:14px;font-weight:500;text-anchor:middle;dominant-baseline:central">Browser</text></g>
<g style="fill:rgb(0, 0, 0);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"><rect x="440" y="904" width="90" height="44" rx="8" stroke-width="0.5" style="fill:rgb(225, 245, 238);stroke:rgb(15, 110, 86);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/><text x="485" y="926" text-anchor="middle" dominant-baseline="central" style="fill:rgb(8, 80, 65);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:14px;font-weight:500;text-anchor:middle;dominant-baseline:central">LLM</text></g>
<g style="fill:rgb(0, 0, 0);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"><rect x="540" y="904" width="90" height="44" rx="8" stroke-width="0.5" style="fill:rgb(225, 245, 238);stroke:rgb(15, 110, 86);color:rgb(11, 11, 11);stroke-width:0.5px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:16px;font-weight:400;text-anchor:start;dominant-baseline:auto"/><text x="585" y="926" text-anchor="middle" dominant-baseline="central" style="fill:rgb(8, 80, 65);stroke:none;color:rgb(11, 11, 11);stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;opacity:1;font-family:anthropic-sans, -apple-system, &quot;system-ui&quot;, &quot;Segoe UI&quot;, sans-serif;font-size:14px;font-weight:500;text-anchor:middle;dominant-baseline:central">Enricher</text></g>
</svg>ad_enrichment_pipeline_sequence.svg…]()


## Why This Exists (And How I Built It)

Most lead scraping tools fall into one of two extremes:
1. **Dumb regex/HTML scrapers** that break the moment a company changes their CSS or uses a Single Page Application (SPA).
2. **Brittle "pure agent" setups** that spend 2 minutes and 50,000 tokens clicking around randomly just to find an "About" page.

I built this pipeline around a **hybrid, two-tier architecture**:
- **The Fast Path (Deterministic & Fast)**: Uses headless Playwright with aggressive asset blocking (dropping images, fonts, and stylesheets) to crawl core navigation and footer links. It strips DOM noise, budgets tokens tightly, and uses Instructor with Groq (`openai/gpt-oss-120b`) for validated, typed Pydantic extraction. Then, it uses Tavily to cross-reference and verify executive LinkedIn profiles.
- **The Deep Path (Agentic & Autonomous)**: When run with `--agentic`, it hands off to a bounded `browser-use` sub-agent. The agent specifically hunts for genuine trigger events—like recent Series A/B funding rounds, leadership changes, or major product launches from the last 12 months—without wasting steps or hallucinating events.

---

## Key Engineering Decisions

### 1. Decoupled Concurrency & Strict Resource Semaphores
Running multiple browser instances while simultaneously hitting LLM inference endpoints easily leads to resource contention and 429 rate limits.
- The pipeline isolates domain workers with `asyncio.gather`, but caps concurrent browser pages and LLM calls via dedicated internal semaphores.
- If a target domain has a dead DNS record, times out, or triggers bot mitigation, the failure is trapped in that domain's isolated error boundary. It records a structured `DomainResult` with the failure reason and execution timings, and the rest of the batch completes uninterrupted.

### 2. Ground-Truth Verification Over Hallucinated Data
LLMs have a bad habit of hallucinating plausible-looking data when given messy HTML. To keep data high quality:
- **Testimonial Rejection**: Filters out customer quotes masquerading as company executives (e.g. customer testimonials on landing pages).
- **Brand & Company Disambiguation**: Cross-checks executive LinkedIn search results against the target company's actual brand and domain, discarding people with matching names who work at completely different firms.
- **Strict Name-to-Slug Matching**: Ensures returned LinkedIn URLs actually match the person's name rather than returning a generic directory or unrelated profile.
- **Clean Inboxes**: Validates email format and strips trailing punctuation, junk characters, and documentation placeholders (`example.com`, `domain.com`).

### 3. Grounded Confidence Scoring
Instead of asking an LLM "how confident are you?" (which almost always answers 0.95+), the confidence score is calculated deterministically from verified signals:
- Base score is awarded for presence and quality of core fields (overview, target audience, verified emails, executive team).
- For agentic trigger events, confidence requires strict corroboration:
  - **No Bare Homepage Citations**: The agent cannot cite `https://company.com/` for a funding round; it must point to the specific blog post, press release, or changelog URL.
  - **Substantive Text Overlap**: Summary keywords must genuinely appear in the visited page text (using word-boundary matching so words like `fundamental` don't trigger a false positive for `fund`).
  - Unsubstantiated or ungrounded claims are strictly hard-capped at $\le 0.30$.

### 4. Token & Cost Efficiency
- Preprocessing token budgeting keeps prompt payloads compact (~1,000 tokens per domain).
- Average cost runs at less than **$0.001 per domain** on the core extraction path, with execution times hovering around 6–12 seconds per domain.

---

## Quick Start

### 1. Prerequisites & Installation

```bash
# Clone the repository
git clone https://github.com/rizzler13/softwarebrio_lead.git
cd softwarebrio_lead

# Install dependencies (requires Python 3.11+)
pip install -e ".[dev]"

# Install Playwright Chromium binaries
playwright install chromium
```

### 2. Environment Configuration

Copy the sample environment file:
```bash
cp .env.example .env
```

Add your API keys to `.env`:
```env
# Required: Fast LLM extraction via Groq (e.g. openai/gpt-oss-120b)
GROQ_API_KEY=gsk_your_groq_key_here

# Optional: Executive LinkedIn discovery & verification
TAVILY_API_KEY=tvly-your_tavily_key_here

# Optional: For agentic mode using OpenAI/OpenRouter models
OPENROUTER_API_KEY=sk-or-your_openrouter_key_here
```

---

## Running the Pipeline

### Core Mode (Fast & Deterministic)
Extracts structured company overview, target audience, verified inboxes, and executive leadership profiles:
```bash
python -m lead_enrich --domains "vapi.ai, supabase.com, postman.com"
```

### Agentic Mode (Autonomous Trigger Discovery)
Spawns the `browser-use` agent to actively navigate the company's site, hunt down blog/press pages, and extract verified trigger events from the last 12 months:
```bash
python -m lead_enrich --domains "vapi.ai, supabase.com" --agentic
```

### Choosing an LLM Provider for the Trigger Agent
You can specify the LLM backend for the agentic stage via `--provider`:
```bash
# Auto mode: prompts interactively or picks based on available keys
python -m lead_enrich --domains "vapi.ai --agentic --provider auto

# Use OpenRouter (gpt-4o-mini) with Groq fallback
python -m lead_enrich --domains "vapi.ai" --agentic --provider both

# Force Groq only (groq/compound) or OpenRouter only
python -m lead_enrich --domains "vapi.ai" --agentic --provider groq
```

### Naming Runs & Inspecting Results
Give your run a clean identifier and open the resulting files automatically:
```bash
# Runs the batch, saves outputs as run_demo.*, and opens in VS Code
python -m lead_enrich --domains "vapi.ai, supabase.com" --name demo --open
```

### CLI Options

| Flag | Shorthand | Description |
| :--- | :---: | :--- |
| `--domains` | | Comma-separated domains to process (e.g. `"linear.app,stripe.com"`). |
| `--agentic` | | Enables the autonomous browser agent for trigger event discovery. |
| `--provider` | | Trigger agent LLM: `auto`, `both`, `openrouter`, or `groq`. |
| `--name` | `-n` | Custom run name identifier (e.g. `--name batch1` $\rightarrow$ `run_batch1.json`). |
| `--open` | | Automatically opens the generated JSON and CSV in your editor. |
| `--verbose` | `-v` | Enables detailed, step-by-step logs of browser and agent actions. |

---

## Output Structure

Every run creates isolated artifacts in `output/runs/` and appends to a cumulative master archive:

```
output/
├── all_leads.csv              # Cumulative master CSV of all runs
├── all_leads.json             # Cumulative master JSON of all runs
└── runs/
    ├── run_<id>.json          # Full structured JSON for this run
    ├── run_<id>.csv           # Flat CSV export formatted for CRM / SDR ingestion
    └── manifest_<id>.json     # Run metadata, timings, model name, and token cost breakdown
```

### Sample Lead Record Schema

```json
{
  "domain": "linear.app",
  "status": "success",
  "error_reason": null,
  "intel": {
    "company_overview": "Purpose-built tool for modern software development teams...",
    "target_audience": "Software engineering, product management, and design teams.",
    "contact_emails": ["support@linear.app", "sales@linear.app"],
    "key_team_members": [
      {
        "name": "Karri Saarinen",
        "role": "Co-Founder & CEO",
        "linkedin_url": "https://www.linkedin.com/in/karrisaarinen"
      }
    ],
    "confidence_score": 0.82,
    "trigger_event": {
      "found": true,
      "event_type": "product_news",
      "summary": "Announced Linear Asks and new customer support integrations.",
      "source_url": "https://linear.app/blog/linear-asks",
      "estimated_date": "2026-04",
      "confidence": 0.80
    }
  },
  "token_usage": {
    "prompt_tokens": 660,
    "completion_tokens": 285,
    "total_tokens": 945,
    "cost_usd": 0.00062
  },
  "timings": {
    "fetch_s": 2.4,
    "preprocess_s": 0.1,
    "llm_s": 1.2,
    "enrich_s": 2.1,
    "trigger_s": 5.5,
    "total_s": 11.3
  }
}
```

---

## Testing & Quality

The project includes a comprehensive test suite (46 automated tests) covering Pydantic models, DOM preprocessing, LinkedIn title parsing, trigger agent degradation, and confidence scoring:

```bash
# Run tests
pytest

# Run linter and formatting checks
ruff check src/ tests/
ruff format --check src/ tests/
```

---

## Architecture Flow

```
                 Input: Comma-separated domains
                               │
               Orchestrator (asyncio.gather)
             Bounded Concurrency & Error Bounds
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
         Domain Worker A               Domain Worker B
                │
   1. discover_urls()       Playwright link discovery & footer crawl
                │
   2. fetch_all_pages()     Parallel page fetch with asset blocking
                │
   3. prepare_llm_input()   Noise stripping & 1000-token budget packing
                │
   4. extract_company()     Instructor + Groq structured extraction
                │
        ┌───────┴────────────────────────┐
        ▼ (concurrent)                   ▼ (concurrent, optional)
   5a. enrich_linkedin()            5b. discover_trigger_event()
       Tavily search & slug match       Browser-Use agent (bounded budget)
        └───────┬────────────────────────┘
                │
   6. compute_confidence()  Grounded multi-signal confidence scoring
                │
   7. write_run_output()    run_<id>.json, run_<id>.csv, manifest_<id>.json
```
