import React, { useEffect, useMemo, useState } from "react";

const API = "/api";
const money = (n) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(n || 0));
const readToken = () => localStorage.getItem("stockpilot_token") || "";
const saveToken = (t) => t ? localStorage.setItem("stockpilot_token", t) : localStorage.removeItem("stockpilot_token");

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = readToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  const response = await fetch(`${API}${path}`, { ...options, headers });
  const raw = await response.text();
  let data = {};
  try { data = raw ? JSON.parse(raw) : {}; } catch { data = { detail: raw || "Unexpected server response" }; }
  if (!response.ok) {
    if (response.status === 401) {
      saveToken("");
      window.dispatchEvent(new Event("auth-expired"));
    }
    throw new Error(data.detail || data.message || `Request failed (${response.status})`);
  }
  return data;
}

function Icon({ children }) { return <span className="icon" aria-hidden="true">{children}</span>; }
function Button({ children, kind = "primary", ...props }) { return <button className={`btn ${kind}`} {...props}>{children}</button>; }
function Field({ label, ...props }) { return <label className="field"><span>{label}</span><input {...props} /></label>; }
function SelectField({ label, children, ...props }) { return <label className="field"><span>{label}</span><select {...props}>{children}</select></label>; }
function Notice({ notice, clear }) {
  if (!notice) return null;
  return <div className={`notice ${notice.type}`}><span>{notice.text}</span><button onClick={clear}>×</button></div>;
}

function AuthScreen({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("test@example.com");
  const [password, setPassword] = useState("Test@12345");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      if (mode === "register") {
        await request("/register", { method: "POST", body: JSON.stringify({ name, email, password }) });
      }
      const body = new URLSearchParams({ username: email, password });
      const result = await request("/login", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body });
      saveToken(result.access_token);
      onLogin();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <div className="auth-wrap">
    <div className="auth-art">
      <div className="brand light"><span className="brand-mark">S</span><span>StockPilot</span></div>
      <div className="art-copy"><div className="eyebrow">INVENTORY CONTROL CENTER</div><h1>Know your stock.<br/>Move with confidence.</h1><p>A single workspace for products, warehouses, orders and payments.</p></div>
      <div className="art-stats"><div><b>01</b><span>Products</span></div><div><b>02</b><span>Inventory</span></div><div><b>03</b><span>Orders</span></div></div>
      <div className="art-orb orb-one"></div><div className="art-orb orb-two"></div>
    </div>
    <div className="auth-panel">
      <div className="mobile-brand brand"><span className="brand-mark">S</span><span>StockPilot</span></div>
      <div className="auth-card">
        <div className="eyebrow">WELCOME</div>
        <h2>{mode === "login" ? "Sign in to your workspace" : "Create your workspace account"}</h2>
        <p className="muted">Use your Inventory Order Platform account.</p>
        <div className="tabs"><button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Sign in</button><button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Register</button></div>
        <form onSubmit={submit} className="stack">
          {mode === "register" && <Field label="Full name" value={name} onChange={e => setName(e.target.value)} placeholder="Your name" required minLength="2" />}
          <Field label="Email address" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" required />
          <Field label="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength="8" />
          {error && <div className="inline-error">{error}</div>}
          <Button disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in →" : "Create account →"}</Button>
        </form>
        <div className="auth-foot">Connected to your local FastAPI server</div>
      </div>
    </div>
  </div>;
}

const navItems = [
  ["dashboard", "▦", "Overview"],
  ["products", "◇", "Products"],
  ["warehouses", "▤", "Warehouses"],
  ["inventory", "▥", "Inventory"],
  ["orders", "↗", "Orders"],
];

export default function App() {
  const [token, setToken] = useState(readToken());
  const [page, setPage] = useState("dashboard");
  const [profile, setProfile] = useState(null);
  const [notice, setNotice] = useState(null);
  const [loading, setLoading] = useState(false);
  const [products, setProducts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [orders, setOrders] = useState([]);

  useEffect(() => {
    const expired = () => { setToken(""); setProfile(null); setNotice({ type: "error", text: "Session expired. Please sign in again." }); };
    window.addEventListener("auth-expired", expired);
    return () => window.removeEventListener("auth-expired", expired);
  }, []);

  async function loadAll() {
    setLoading(true);
    try {
      const [me, p, w, i, o] = await Promise.all([
        request("/me"), request("/products"), request("/warehouses"), request("/inventory"), request("/orders")
      ]);
      setProfile(me);
      setProducts(p.products || []);
      setWarehouses(w.warehouses || []);
      setInventory(i.inventory || []);
      setOrders(o.orders || []);
    } catch (err) { setNotice({ type: "error", text: err.message }); }
    finally { setLoading(false); }
  }
  useEffect(() => { if (token) loadAll(); }, [token]);
  const refresh = async () => { await loadAll(); };
  const notify = (text, type = "success") => setNotice({ text, type });

  async function logout() { saveToken(""); setToken(""); setProfile(null); setPage("dashboard"); }
  if (!token) return <AuthScreen onLogin={() => { setToken(readToken()); setNotice({ type: "success", text: "Signed in successfully." }); }} />;

  const totalUnits = inventory.reduce((s, x) => s + Number(x.quantity || 0), 0);
  const lowStock = inventory.filter(x => Number(x.quantity) <= 10).length;
  const pendingOrders = orders.filter(x => x.status === "PENDING").length;
  const totalValue = orders.reduce((s, x) => s + Number(x.total_amount || 0), 0);

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">S</span><span>StockPilot</span></div>
      <div className="workspace-label">WORKSPACE</div>
      <nav>{navItems.map(([id, icon, label]) => <button key={id} className={`nav-link ${page === id ? "selected" : ""}`} onClick={() => setPage(id)}><span className="nav-icon">{icon}</span>{label}{id === "orders" && pendingOrders > 0 && <em>{pendingOrders}</em>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="api-status"><i></i><div><b>API connected</b><small>localhost:8000</small></div></div><button className="nav-link" onClick={refresh}><span className="nav-icon">↻</span>Refresh data</button><button className="nav-link" onClick={logout}><span className="nav-icon">⇥</span>Sign out</button></div>
    </aside>
    <main className="main-area">
      <header className="topbar"><div><span className="breadcrumb">Workspace</span><span className="crumb-sep">/</span><b>{navItems.find(x => x[0] === page)?.[2]}</b></div><div className="top-user"><div className="avatar">{(profile?.name || "U").slice(0,1).toUpperCase()}</div><div><b>{profile?.name || "User"}</b><small>{profile?.role || "STAFF"}</small></div><button className="icon-button" title="Refresh" onClick={refresh}>↻</button></div></header>
      <div className="content">
        <Notice notice={notice} clear={() => setNotice(null)} />
        {loading && <div className="loading-line">Syncing with FastAPI…</div>}
        {page === "dashboard" && <Dashboard products={products} warehouses={warehouses} inventory={inventory} orders={orders} totalUnits={totalUnits} lowStock={lowStock} pendingOrders={pendingOrders} totalValue={totalValue} setPage={setPage} />}
        {page === "products" && <Products products={products} refresh={refresh} notify={notify} />}
        {page === "warehouses" && <Warehouses warehouses={warehouses} refresh={refresh} notify={notify} />}
        {page === "inventory" && <Inventory inventory={inventory} products={products} warehouses={warehouses} refresh={refresh} notify={notify} />}
        {page === "orders" && <Orders orders={orders} products={products} refresh={refresh} notify={notify} />}
      </div>
      <footer className="footer">StockPilot <span>•</span> Inventory & Order Management <span className="footer-right">Powered by FastAPI</span></footer>
    </main>
  </div>;
}

function PageHeading({ eyebrow, title, subtitle, action }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>;
}
function Dashboard({ products, warehouses, inventory, orders, totalUnits, lowStock, pendingOrders, totalValue, setPage }) {
  const recent = [...orders].slice(-5).reverse();
  return <>
    <PageHeading eyebrow="OVERVIEW" title="Good to see you." subtitle="Here’s what’s happening across your inventory today." action={<Button kind="secondary" onClick={() => setPage("orders")}>View all orders ↗</Button>} />
    <div className="welcome-strip"><div><div className="welcome-label">INVENTORY SNAPSHOT</div><h2>Your operations, at a glance.</h2><p>Monitor stock levels and keep orders moving smoothly.</p></div><div className="welcome-symbol">▦</div></div>
    <div className="stats-grid">
      <Stat label="Total products" value={products.length} hint="Catalog items" icon="◇" tone="blue"/>
      <Stat label="Stock on hand" value={totalUnits.toLocaleString("en-IN")} hint="Across all locations" icon="▥" tone="green"/>
      <Stat label="Pending orders" value={pendingOrders} hint={`${orders.length} total orders`} icon="↗" tone="orange"/>
      <Stat label="Order value" value={money(totalValue)} hint="All recorded orders" icon="₹" tone="purple"/>
    </div>
    <div className="dashboard-grid">
      <section className="panel"><div className="panel-head"><div><h3>Recent orders</h3><p>Latest activity from your order book</p></div><button className="text-button" onClick={() => setPage("orders")}>See all →</button></div>
        {recent.length ? <div className="table-wrap"><table><thead><tr><th>ORDER</th><th>STATUS</th><th>AMOUNT</th></tr></thead><tbody>{recent.map(o => <tr key={o.order_id}><td><b>#{o.order_number}</b><small>Order ID {o.order_id}</small></td><td><Status status={o.status}/></td><td className="amount">{money(o.total_amount)}</td></tr>)}</tbody></table></div> : <Empty text="No orders yet. Create your first order from the Orders page."/>}
      </section>
      <section className="panel"><div className="panel-head"><div><h3>Stock health</h3><p>Quick inventory overview</p></div></div>
        <div className="health-row"><div className="health-icon green-bg">▥</div><div className="health-copy"><b>{totalUnits.toLocaleString("en-IN")} units</b><small>Total available stock</small></div><strong>{inventory.length} records</strong></div>
        <div className="health-row"><div className="health-icon orange-bg">!</div><div className="health-copy"><b>{lowStock} low-stock records</b><small>10 units or fewer</small></div><strong className={lowStock ? "warning-text" : "success-text"}>{lowStock ? "Review" : "Healthy"}</strong></div>
        <div className="health-row"><div className="health-icon blue-bg">▤</div><div className="health-copy"><b>{warehouses.length} warehouses</b><small>Storage locations</small></div><strong>{warehouses.filter(w => w.is_active).length} active</strong></div>
        <div className="quick-actions"><button onClick={() => setPage("products")}>＋ Add product</button><button onClick={() => setPage("inventory")}>＋ Add stock</button></div>
      </section>
    </div>
  </>;
}
function Stat({ label, value, hint, icon, tone }) {
  return <div className="stat-card"><div className={`stat-icon ${tone}`}>{icon}</div><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-hint">{hint}</div></div>;
}
function Status({ status }) { return <span className={`status ${String(status || "UNKNOWN").toLowerCase()}`}>{status || "UNKNOWN"}</span>; }
function Empty({ text }) { return <div className="empty"><div>◌</div><b>Nothing here yet</b><p>{text}</p></div>; }

function Products({ products, refresh, notify }) {
  const [form, setForm] = useState({ name: "", sku: "", category: "", price: "", stock_quantity: 0 });
  const [busy, setBusy] = useState(false);
  const [show, setShow] = useState(false);
  async function create(e) {
    e.preventDefault(); setBusy(true);
    try { await request("/products", { method: "POST", body: JSON.stringify({ ...form, price: Number(form.price), stock_quantity: Number(form.stock_quantity) }) }); setForm({ name: "", sku: "", category: "", price: "", stock_quantity: 0 }); setShow(false); await refresh(); notify("Product created successfully."); }
    catch (e) { notify(e.message, "error"); } finally { setBusy(false); }
  }
  async function remove(id) {
    if (!confirm(`Delete product ${id}?`)) return;
    try { await request(`/products/${id}`, { method: "DELETE" }); await refresh(); notify("Product deleted."); } catch(e) { notify(e.message, "error"); }
  }
  return <><PageHeading eyebrow="CATALOG" title="Products" subtitle="Manage the items your business stocks and sells." action={<Button onClick={() => setShow(!show)}>＋ Add product</Button>} />
    {show && <form className="panel form-panel" onSubmit={create}><div className="panel-head"><div><h3>New product</h3><p>Enter the product details below.</p></div><button type="button" className="icon-button" onClick={() => setShow(false)}>×</button></div><div className="form-grid"><Field label="Product name" value={form.name} onChange={e=>setForm({...form,name:e.target.value})} required minLength="2"/><Field label="SKU" value={form.sku} onChange={e=>setForm({...form,sku:e.target.value})} required minLength="3"/><Field label="Category" value={form.category} onChange={e=>setForm({...form,category:e.target.value})} required/><Field label="Price (INR)" type="number" min="0.01" step="0.01" value={form.price} onChange={e=>setForm({...form,price:e.target.value})} required/><Field label="Initial stock quantity" type="number" min="0" value={form.stock_quantity} onChange={e=>setForm({...form,stock_quantity:e.target.value})}/></div><div className="form-actions"><Button type="button" kind="secondary" onClick={()=>setShow(false)}>Cancel</Button><Button disabled={busy}>{busy ? "Saving…" : "Save product"}</Button></div></form>}
    <section className="panel"><div className="panel-head"><div><h3>Product catalog</h3><p>{products.length} products registered</p></div></div>{products.length ? <div className="table-wrap"><table><thead><tr><th>PRODUCT</th><th>SKU</th><th>CATEGORY</th><th>PRICE</th><th>STOCK FIELD</th><th></th></tr></thead><tbody>{products.map(p=><tr key={p.id}><td><div className="product-cell"><span className="product-thumb">◇</span><b>{p.name}</b></div><small>ID {p.id}</small></td><td><code>{p.sku}</code></td><td>{p.category}</td><td className="amount">{money(p.price)}</td><td>{p.stock_quantity}</td><td><button className="danger-link" onClick={()=>remove(p.id)}>Delete</button></td></tr>)}</tbody></table></div> : <Empty text="Add a product to start building your catalog."/>}</section>
  </>;
}

function Warehouses({ warehouses, refresh, notify }) {
  const [form,setForm]=useState({name:"",location:""}); const [show,setShow]=useState(false); const [busy,setBusy]=useState(false);
  async function create(e){e.preventDefault();setBusy(true);try{await request("/warehouses",{method:"POST",body:JSON.stringify(form)});setForm({name:"",location:""});setShow(false);await refresh();notify("Warehouse created.");}catch(e){notify(e.message,"error");}finally{setBusy(false);}}
  return <><PageHeading eyebrow="LOCATIONS" title="Warehouses" subtitle="Organize storage locations and track where stock lives." action={<Button onClick={()=>setShow(!show)}>＋ Add warehouse</Button>}/>{show&&<form className="panel form-panel" onSubmit={create}><div className="panel-head"><div><h3>New warehouse</h3><p>Create a storage location.</p></div></div><div className="form-grid two"><Field label="Warehouse name" value={form.name} onChange={e=>setForm({...form,name:e.target.value})} required/><Field label="Location" value={form.location} onChange={e=>setForm({...form,location:e.target.value})} required/></div><div className="form-actions"><Button type="button" kind="secondary" onClick={()=>setShow(false)}>Cancel</Button><Button disabled={busy}>{busy?"Saving…":"Save warehouse"}</Button></div></form>}
    <div className="warehouse-grid">{warehouses.map(w=><div className="warehouse-card" key={w.id}><div className="warehouse-symbol">▤</div><div className="warehouse-status"><i className={w.is_active?"":"inactive"}></i>{w.is_active?"Active":"Inactive"}</div><h3>{w.name}</h3><p>⌖ {w.location}</p><small>Warehouse ID {w.id}</small></div>)}</div>{!warehouses.length&&<section className="panel"><Empty text="Create your first warehouse to organize inventory."/></section>}</>;
}

function Inventory({ inventory, products, warehouses, refresh, notify }) {
  const [form,setForm]=useState({product_id:"",warehouse_id:"",quantity:""}); const [movement,setMovement]=useState({inventory_id:"",transaction_type:"STOCK_IN",quantity:""}); const [show,setShow]=useState(false); const [showMove,setShowMove]=useState(false); const [busy,setBusy]=useState(false);
  async function create(e){e.preventDefault();setBusy(true);try{await request("/inventory",{method:"POST",body:JSON.stringify({product_id:Number(form.product_id),warehouse_id:Number(form.warehouse_id),quantity:Number(form.quantity)})});setShow(false);setForm({product_id:"",warehouse_id:"",quantity:""});await refresh();notify("Inventory record created.");}catch(e){notify(e.message,"error");}finally{setBusy(false);}}
  async function move(e){e.preventDefault();setBusy(true);try{await request("/inventory/movement",{method:"POST",body:JSON.stringify({inventory_id:Number(movement.inventory_id),transaction_type:movement.transaction_type,quantity:Number(movement.quantity)})});setShowMove(false);setMovement({inventory_id:"",transaction_type:"STOCK_IN",quantity:""});await refresh();notify("Stock movement recorded.");}catch(e){notify(e.message,"error");}finally{setBusy(false);}}
  const productName=(id)=>products.find(p=>p.id===id)?.name || `Product ${id}`;
  const warehouseName=(id)=>warehouses.find(w=>w.id===id)?.name || `Warehouse ${id}`;
  return <><PageHeading eyebrow="STOCK CONTROL" title="Inventory" subtitle="See available units by product and warehouse." action={<div className="heading-actions"><Button kind="secondary" onClick={()=>setShowMove(!showMove)}>↕ Stock movement</Button><Button onClick={()=>setShow(!show)}>＋ Add inventory</Button></div>}/>
    {show&&<form className="panel form-panel" onSubmit={create}><div className="panel-head"><div><h3>Add inventory record</h3><p>Assign product stock to a warehouse.</p></div></div><div className="form-grid three"><SelectField label="Product" value={form.product_id} onChange={e=>setForm({...form,product_id:e.target.value})} required><option value="">Select product</option>{products.map(p=><option value={p.id} key={p.id}>{p.name} (#{p.id})</option>)}</SelectField><SelectField label="Warehouse" value={form.warehouse_id} onChange={e=>setForm({...form,warehouse_id:e.target.value})} required><option value="">Select warehouse</option>{warehouses.map(w=><option value={w.id} key={w.id}>{w.name}</option>)}</SelectField><Field label="Quantity" type="number" min="0" value={form.quantity} onChange={e=>setForm({...form,quantity:e.target.value})} required/></div><div className="form-actions"><Button type="button" kind="secondary" onClick={()=>setShow(false)}>Cancel</Button><Button disabled={busy}>Save inventory</Button></div></form>}
    {showMove&&<form className="panel form-panel" onSubmit={move}><div className="panel-head"><div><h3>Record stock movement</h3><p>Stock-in adds units; stock-out removes units.</p></div></div><div className="form-grid three"><SelectField label="Inventory record" value={movement.inventory_id} onChange={e=>setMovement({...movement,inventory_id:e.target.value})} required><option value="">Select record</option>{inventory.map(i=><option value={i.id} key={i.id}>#{i.id} · {productName(i.product_id)} ({i.quantity} units)</option>)}</SelectField><SelectField label="Movement type" value={movement.transaction_type} onChange={e=>setMovement({...movement,transaction_type:e.target.value})}><option value="STOCK_IN">Stock in</option><option value="STOCK_OUT">Stock out</option></SelectField><Field label="Quantity" type="number" min="1" value={movement.quantity} onChange={e=>setMovement({...movement,quantity:e.target.value})} required/></div><div className="form-actions"><Button type="button" kind="secondary" onClick={()=>setShowMove(false)}>Cancel</Button><Button disabled={busy}>Record movement</Button></div></form>}
    <section className="panel"><div className="panel-head"><div><h3>Stock by location</h3><p>{inventory.length} inventory records</p></div></div>{inventory.length?<div className="table-wrap"><table><thead><tr><th>PRODUCT</th><th>WAREHOUSE</th><th>AVAILABLE</th><th>STOCK LEVEL</th><th>RECORD ID</th></tr></thead><tbody>{inventory.map(i=><tr key={i.id}><td><div className="product-cell"><span className="product-thumb">◇</span><b>{productName(i.product_id)}</b></div><small>Product ID {i.product_id}</small></td><td>{warehouseName(i.warehouse_id)}</td><td className="amount">{i.quantity} units</td><td><div className="stock-bar"><i style={{width:`${Math.min(100,Number(i.quantity))}%`}} className={i.quantity<=10?"low":""}></i></div><small className={i.quantity<=10?"warning-text":"muted"}>{i.quantity<=10?"Low stock":"In stock"}</small></td><td>#{i.id}</td></tr>)}</tbody></table></div>:<Empty text="Add inventory records to see stock levels here."/>}</section>
  </>;
}

function Orders({ orders, products, refresh, notify }) {
  const [show,setShow]=useState(false); const [busy,setBusy]=useState(false); const [lines,setLines]=useState([{product_id:"",quantity:1}]);
  const [paymentBusy,setPaymentBusy]=useState(null);
  const productMap=useMemo(()=>Object.fromEntries(products.map(p=>[p.id,p])),[products]);
  function updateLine(index,key,value){setLines(old=>old.map((x,i)=>i===index?{...x,[key]:value}:x));}
  async function create(e){e.preventDefault();setBusy(true);try{const result=await request("/orders",{method:"POST",body:JSON.stringify({items:lines.map(x=>({product_id:Number(x.product_id),quantity:Number(x.quantity)}))})});setShow(false);setLines([{product_id:"",quantity:1}]);await refresh();notify(`Order ${result.order_number} created.`);}catch(e){notify(e.message,"error");}finally{setBusy(false);}}
  async function cancel(id){if(!confirm(`Cancel order ${id}? Stock will be restored if cancellation is allowed.`))return;try{await request(`/orders/${id}/cancel`,{method:"POST"});await refresh();notify(`Order ${id} cancelled and stock restoration processed.`);}catch(e){notify(e.message,"error");}}
  async function pay(id){setPaymentBusy(id);try{
    const created=await request(`/orders/${id}/payments/razorpay`,{method:"POST"});
    const scriptOk=await loadRazorpay();
    if(!scriptOk) throw new Error("Could not load Razorpay Checkout. Check internet connection.");
    const checkout=new window.Razorpay({
      key:created.razorpay_key_id,
      amount:created.amount,
      currency:created.currency || "INR",
      name:"StockPilot",
      description:`Payment for order #${id}`,
      order_id:created.razorpay_order_id,
      handler:async function(response){
        try{
          const verified=await request("/payments/razorpay/verify",{method:"POST",body:JSON.stringify({
            razorpay_order_id:response.razorpay_order_id,
            razorpay_payment_id:response.razorpay_payment_id,
            razorpay_signature:response.razorpay_signature
          })});
          notify(verified.message || "Payment verified successfully.");
          await refresh();
        }catch(err){notify(`Payment received but verification failed: ${err.message}`,"error");}
      },
      modal:{ondismiss:()=>notify("Checkout closed. Order remains pending until payment is completed.","error")},
      theme:{color:"#635bff"}
    });
    checkout.open();
  }catch(e){notify(e.message,"error");}finally{setPaymentBusy(null);}}
  return <><PageHeading eyebrow="SALES" title="Orders" subtitle="Create customer orders, monitor status and collect payments." action={<Button onClick={()=>setShow(!show)}>＋ Create order</Button>}/>
    {show&&<form className="panel form-panel" onSubmit={create}><div className="panel-head"><div><h3>New order</h3><p>Add one or more products. Stock is reserved by the API.</p></div></div>{lines.map((line,index)=><div className="order-line" key={index}><SelectField label="Product" value={line.product_id} onChange={e=>updateLine(index,"product_id",e.target.value)} required><option value="">Select product</option>{products.map(p=><option key={p.id} value={p.id}>{p.name} · {money(p.price)}</option>)}</SelectField><Field label="Quantity" type="number" min="1" value={line.quantity} onChange={e=>updateLine(index,"quantity",e.target.value)} required/><button type="button" className="danger-link" disabled={lines.length===1} onClick={()=>setLines(old=>old.filter((_,i)=>i!==index))}>Remove</button></div>)}<button type="button" className="text-button add-line" onClick={()=>setLines(old=>[...old,{product_id:"",quantity:1}])}>＋ Add another item</button><div className="form-actions"><Button type="button" kind="secondary" onClick={()=>setShow(false)}>Cancel</Button><Button disabled={busy||!products.length}>{busy?"Creating…":"Create order"}</Button></div></form>}
    <section className="panel"><div className="panel-head"><div><h3>Order register</h3><p>{orders.length} orders in the system</p></div></div>{orders.length?<div className="table-wrap"><table><thead><tr><th>ORDER</th><th>CREATED</th><th>STATUS</th><th>TOTAL</th><th>ACTIONS</th></tr></thead><tbody>{[...orders].reverse().map(o=><tr key={o.order_id}><td><b>{o.order_number}</b><small>Order ID {o.order_id}</small></td><td>{o.created_at?new Date(o.created_at).toLocaleString():"—"}</td><td><Status status={o.status}/></td><td className="amount">{money(o.total_amount)}</td><td><div className="row-actions">{o.status==="PENDING"&&<><Button kind="small" onClick={()=>pay(o.order_id)} disabled={paymentBusy===o.order_id}>{paymentBusy===o.order_id?"Opening…":"Pay"}</Button><button className="danger-link" onClick={()=>cancel(o.order_id)}>Cancel</button></>}</div></td></tr>)}</tbody></table></div>:<Empty text="Create an order to see it listed here."/>}</section>
    <div className="info-note"><b>Razorpay test checkout</b><span>Click Pay on a pending order. Checkout opens in test mode using the key returned by your FastAPI endpoint. Payment status updates only after backend signature verification.</span></div>
  </>;
}

let razorpayPromise;
function loadRazorpay() {
  if (window.Razorpay) return Promise.resolve(true);
  if (!razorpayPromise) razorpayPromise = new Promise(resolve => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
  return razorpayPromise;
}
