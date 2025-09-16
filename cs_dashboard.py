import streamlit as st
import db
import pandas as pd

# ===== Init DB & session =====
db.init_db()

st.set_page_config(page_title="CS QnA", layout="wide")
st.title("CS QnA Dashboard")

# Load CS list dari DB
if "cs_list" not in st.session_state:
    st.session_state.cs_list = db.get_cs_list()

# Sidebar CS management
st.sidebar.header("Manajemen CS")
for cs in st.session_state.cs_list:
    st.sidebar.write(f"- {cs}")

# Tambah CS
new_cs = st.sidebar.text_input("Tambah CS baru")
if st.sidebar.button("Tambah CS") and new_cs:
    if new_cs not in st.session_state.cs_list:
        db.add_cs(new_cs)
        st.session_state.cs_list = db.get_cs_list()
        st.sidebar.success(f"{new_cs} ditambahkan!")
    else:
        st.sidebar.warning(f"{new_cs} sudah ada!")

# Hapus CS
cs_to_remove = st.sidebar.selectbox("Hapus CS", ["-"] + st.session_state.cs_list)
if st.sidebar.button("Hapus CS") and cs_to_remove != "-":
    db.remove_cs(cs_to_remove)
    st.session_state.cs_list = db.get_cs_list()
    st.sidebar.success(f"{cs_to_remove} dihapus!")

# ===== Ambil data fresh dari DB =====
all_qs = db.get_questions()
# Filter Pending & History berdasarkan status
pending_qs = [q for q in all_qs if q[4] == "pending"]
history_qs = [q for q in all_qs if q[4] in ("answered", "replied", "closed")]

# ===== Tabs =====
tab1, tab2 = st.tabs(["Pending", "History"])

# ================= TAB 1 - Pending =================
with tab1:
    st.subheader("Daftar Pertanyaan Pending")

    if not pending_qs:
        st.info("Tidak ada pertanyaan pending.")
    else:
        # Buat DataFrame dengan semua kolom
        df_pending = pd.DataFrame(pending_qs, columns=[
            "ID", "Pertanyaan", "Chat ID", "Sender Name", "Status",
            "Jawaban", "Timestamp", "Nama CS", "Message ID", "Closed Reason"
        ])
        # Tampilkan subset kolom
        df_pending_show = df_pending[["ID", "Timestamp", "Sender Name", "Pertanyaan", "Nama CS", "Status"]]
        st.dataframe(df_pending_show, use_container_width=True)

        # Pilih pertanyaan (opsi kosong dulu)
        pilih_id = st.selectbox("Pilih ID Pertanyaan", ["-"] + df_pending_show["ID"].astype(str).tolist())

        if pilih_id != "-":
            pilih_id = int(pilih_id)
            selected_row = df_pending[df_pending["ID"] == pilih_id].iloc[0]

            # Tampilkan detail pertanyaan
            st.markdown("###Pertanyaan:")
            st.info(selected_row["Pertanyaan"])

            # Pilih CS
            selected_cs = st.selectbox("Pilih CS", st.session_state.cs_list)

            # Pilih Tindakan
            options = {
                "Diteruskan ke Admin": "Halo, pertanyaan PO ini sudah diteruskan ke admin. Kami akan mengabari Anda begitu ada update.",
                "Sedang di-follow up": "Pertanyaan PO ini sedang ditindaklanjuti, mohon ditunggu informasi selanjutnya.",
                "Follow up selesai": "Follow up pertanyaan PO ini sudah selesai. Mohon cek informasi terakhir atau konfirmasi jika perlu.",
                "Ditutup / Resolved": "Pertanyaan PO ini sudah selesai dan ditutup. Terima kasih atas kesabarannya!",
                "Perlu info tambahan": "CS membutuhkan informasi tambahan dari Anda agar bisa menindaklanjuti pertanyaan PO ini. Mohon lengkapi detailnya.",
                "Eskalasi ke Tim Lain": "Pertanyaan PO ini sedang diteruskan ke tim terkait. Kami akan mengabari begitu ada update."
            }
            selected_option = st.selectbox("Pilih Tindakan", list(options.keys()) + ["Custom..."])

            if selected_option == "Custom...":
                final_answer = st.text_area("Jawaban Custom")
            else:
                final_answer = options[selected_option]

            if st.button("Kirim Jawaban"):
                if not final_answer:
                    st.warning("Isi jawaban custom dulu!")
                else:
                    db.update_answer(pilih_id, final_answer, selected_cs, status="answered")
                    st.rerun()

# ================= TAB 2 - History =================
with tab2:
    st.subheader("History Pertanyaan")

    if history_qs:
        df_history = pd.DataFrame(history_qs, columns=[
            "ID", "Pertanyaan", "Chat ID", "Sender Name", "Status",
            "Jawaban", "Timestamp", "Nama CS", "Message ID", "Closed Reason"
        ])
        df_history_show = df_history[["Timestamp", "Sender Name", "Pertanyaan", "Nama CS", "Jawaban", "Status"]]
        st.dataframe(df_history_show, use_container_width=True)
    else:
        st.info("Belum ada history pertanyaan.")
